import pytest
import pandas as pd
import tempfile
import os
from processor import generate_report, sanitize_excel_value, OUTPUT_DIR
from openpyxl import load_workbook


# =========================================================================
# Tests unitaires pour sanitize_excel_value
# =========================================================================

class TestSanitizeExcelValue:
    def test_formula_equals(self):
        assert sanitize_excel_value("=1+1") == "'=1+1"

    def test_formula_hyperlink(self):
        assert sanitize_excel_value('=HYPERLINK("http://evil.com","Click")') == """'=HYPERLINK("http://evil.com","Click")"""

    def test_formula_plus(self):
        assert sanitize_excel_value("+cmd|'/C calc'!A0") == "'+cmd|'/C calc'!A0"

    def test_formula_minus(self):
        assert sanitize_excel_value("-1+1") == "'-1+1"

    def test_formula_at(self):
        assert sanitize_excel_value("@SUM(A1:A10)") == "'@SUM(A1:A10)"

    def test_normal_text_unchanged(self):
        assert sanitize_excel_value("Ticket résolu normalement") == "Ticket résolu normalement"

    def test_empty_string(self):
        assert sanitize_excel_value("") == ""

    def test_none_passthrough(self):
        assert sanitize_excel_value(None) is None

    def test_numeric_passthrough(self):
        assert sanitize_excel_value(42) == 42


# =========================================================================
# Test d'intégration : vérifier que le rapport Excel généré est protégé
# =========================================================================

@pytest.fixture
def excel_with_malicious_resume():
    """Crée un fichier Excel de test contenant des résumés malveillants."""
    data = {
        "Identifiant": [1001, 1002, 1003],
        "Projet": ["SCB_RUN_MON", "SCB_RUN_MON", "SCB_RUN_MON"],
        "Assigné à": ["testuser", "testuser", "testuser"],
        "Date de soumission": ["2026-06-01", "2026-06-02", "2026-06-03"],
        "Mis à jour": ["2026-06-05", "2026-06-06", "2026-06-07"],
        "Résumé": [
            "=1+1",
            '=HYPERLINK("http://evil.com","Click me")',
            "Ticket normal sans injection"
        ],
        "Statut": ["Clôturé", "Clôturé", "Clôturé"],
        "Responsable": ["APP", "APP", "APP"],
        "Sous Domaine MON": [
            "Activation Carte",
            "Activation Carte",
            "Activation Carte"
        ]
    }
    df = pd.DataFrame(data)

    temp_dir = tempfile.gettempdir()
    temp_path = os.path.join(temp_dir, "test_injection.xlsx")

    with pd.ExcelWriter(temp_path, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='RUN+MON', index=False)

    yield temp_path

    if os.path.exists(temp_path):
        try:
            os.remove(temp_path)
        except OSError:
            pass


def test_excel_formula_injection_blocked(excel_with_malicious_resume):
    """Vérifie que les résumés malveillants sont préfixés d'une apostrophe dans le fichier Excel."""
    kpi_stats, output_path = generate_report(
        excel_with_malicious_resume,
        start_date="2026-06-01",
        end_date="2026-06-30",
        date_column="Date de soumission",
        sla_groups=["2"],
        collaborators=["testuser"],
        reference_date="2026-06-30"
    )

    # Ouvrir le fichier Excel généré et lire les cellules Résumé
    wb = load_workbook(output_path)
    ws = wb["Clôturées"]

    # Trouver l'index de la colonne Résumé
    header_row = [cell.value for cell in ws[1]]
    resume_col_idx = header_row.index("Résumé") + 1

    resume_values = []
    for row in range(2, ws.max_row + 1):
        val = ws.cell(row=row, column=resume_col_idx).value
        if val is not None:
            resume_values.append(str(val))

    # Vérifier qu'aucune cellule ne commence par = sans apostrophe
    for val in resume_values:
        if "=1+1" in val or "=HYPERLINK" in val:
            assert val.startswith("'"), f"Cellule non protégée trouvée: {val}"

    # Le ticket normal ne doit PAS être préfixé
    assert any("Ticket normal sans injection" == v for v in resume_values), \
        "Le texte normal a été altéré par la sanitisation"

    wb.close()

    # Cleanup
    if os.path.exists(output_path):
        os.remove(output_path)


def test_all_text_columns_sanitized():
    """Vérifie que tous les champs texte (Projet, Assigné à, Statut, etc.) sont assainis."""
    from app.infrastructure.excel.reader import _TEXT_COLUMNS_TO_SANITIZE
    expected_columns = ["Projet", "Assigné à", "Résumé", "Statut", "Responsable", "Sous Domaine MON"]
    for col in expected_columns:
        assert col in _TEXT_COLUMNS_TO_SANITIZE


def test_security_headers_present():
    """Vérifie la présence et la configuration des 5 security headers."""
    from fastapi.testclient import TestClient
    from app.main import app

    client = TestClient(app)
    response = client.get("/login")

    assert response.headers.get("X-Content-Type-Options") == "nosniff"
    assert response.headers.get("X-Frame-Options") == "DENY"
    assert response.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    assert "max-age=" in response.headers.get("Strict-Transport-Security", "")
    
    csp = response.headers.get("Content-Security-Policy", "")
    assert "default-src 'self'" in csp
    assert "fonts.googleapis.com" in csp
    assert "fonts.gstatic.com" in csp
    assert "cdn.jsdelivr.net" in csp
