import os
import json
import uuid
import shutil

from datetime import datetime, timezone

import pandas as pd

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    HTTPException,
)

from app.api.dependencies import (
    get_current_user,
    User,
)

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings


router = APIRouter(
    prefix="/api",
    tags=["Config"],
)


# ============================================================================
# UPLOAD SECURITY
# ============================================================================

# 500 MiB maximum per uploaded file.
# This is intentionally the only upload-size restriction.
MAX_UPLOAD_SIZE = 500 * 1024 * 1024


def save_upload_with_limit(
    upload_file: UploadFile,
    destination_path: str,
    max_size: int = MAX_UPLOAD_SIZE,
) -> int:
    """
    Saves an uploaded file while enforcing a maximum size.

    The file is read in chunks so we do not rely on Content-Length.
    If the file exceeds the limit, the partial file is deleted and
    HTTP 413 is returned.

    Returns:
        Total number of bytes written.
    """

    total_size = 0
    chunk_size = 1024 * 1024  # 1 MiB

    try:
        with open(
            destination_path,
            "wb",
        ) as buffer:

            while True:
                chunk = upload_file.file.read(
                    chunk_size
                )

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > max_size:
                    raise HTTPException(
                        status_code=413,
                        detail=(
                            "Fichier trop volumineux. "
                            "La taille maximale autorisée est de 500 Mo."
                        ),
                    )

                buffer.write(chunk)

    except HTTPException:
        if os.path.exists(
            destination_path
        ):
            os.remove(
                destination_path
            )
        raise

    except Exception:
        if os.path.exists(
            destination_path
        ):
            os.remove(
                destination_path
            )
        raise

    return total_size


# ============================================================================
# SESSION HELPERS
# ============================================================================

def create_session_directory() -> str:
    """
    Creates the root directory used to store upload sessions.
    """

    sessions_dir = os.path.join(
        settings.OUTPUT_DIR,
        "sessions",
    )

    os.makedirs(
        sessions_dir,
        exist_ok=True,
    )

    return sessions_dir


def create_session_metadata(
    session_directory: str,
    session_id: str,
    current_user: User,
    original_file_name: str,
    stored_file_name: str,
):
    """
    Stores ownership and traceability information for an upload session.
    """

    metadata_path = os.path.join(
        session_directory,
        "metadata.json",
    )

    metadata = {
        "session_id": session_id,
        "username": current_user.username,
        "created_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "original_file_name": original_file_name,
        "stored_file_name": stored_file_name,
    }

    with open(
        metadata_path,
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            metadata,
            f,
            ensure_ascii=False,
            indent=2,
        )

    return metadata_path


def is_valid_session_id(
    session_id: str,
) -> bool:
    """
    Session IDs are generated with uuid.uuid4().hex.
    """

    if not isinstance(
        session_id,
        str,
    ):
        return False

    if len(session_id) != 32:
        return False

    return all(
        char in "0123456789abcdefABCDEF"
        for char in session_id
    )


def get_session_directory(
    session_id: str,
) -> str:
    """
    Returns the directory for a given session.
    """

    if not is_valid_session_id(
        session_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Identifiant de session invalide."
            ),
        )

    return os.path.join(
        settings.OUTPUT_DIR,
        "sessions",
        session_id,
    )


def load_session_metadata(
    session_id: str,
) -> dict:
    """
    Loads metadata for a session.
    """

    session_directory = (
        get_session_directory(
            session_id
        )
    )

    metadata_path = os.path.join(
        session_directory,
        "metadata.json",
    )

    if not os.path.exists(
        metadata_path
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Session d'importation "
                "introuvable ou expirée."
            ),
        )

    try:
        with open(
            metadata_path,
            "r",
            encoding="utf-8",
        ) as f:
            metadata = json.load(f)

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Métadonnées de session invalides."
            ),
        )

    return metadata


def get_owned_session(
    session_id: str,
    current_user: User,
) -> tuple[str, dict]:
    """
    Returns the session file path only if the session belongs
    to the currently authenticated user.
    """

    metadata = load_session_metadata(
        session_id
    )

    session_owner = metadata.get(
        "username"
    )

    if (
        session_owner
        != current_user.username
    ):
        raise HTTPException(
            status_code=403,
            detail="Accès interdit.",
        )

    session_directory = (
        get_session_directory(
            session_id
        )
    )

    stored_file_name = metadata.get(
        "stored_file_name"
    )

    if not stored_file_name:
        raise HTTPException(
            status_code=500,
            detail=(
                "Fichier de session "
                "non configuré."
            ),
        )

    session_file_path = os.path.join(
        session_directory,
        stored_file_name,
    )

    if not os.path.exists(
        session_file_path
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Fichier de session "
                "introuvable."
            ),
        )

    return (
        session_file_path,
        metadata,
    )


# ============================================================================
# GET CONFIG
# ============================================================================

@router.get("/config")
def get_config(
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Returns application configuration required by the frontend.
    """

    sla_file = (
        settings.SLA_MAPPING_PATH
    )

    collab_file = (
        settings.COLLABORATORS_PATH
    )

    try:

        with open(
            sla_file,
            "r",
            encoding="utf-8",
        ) as f:
            sla_mapping = json.load(f)

        with open(
            collab_file,
            "r",
            encoding="utf-8",
        ) as f:
            collaborators = json.load(f)

        if not isinstance(
            collaborators,
            list,
        ):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Le fichier des collaborateurs "
                    "doit contenir une liste."
                ),
            )

        return {
            "sla_mapping": sla_mapping,
            "collaborators": collaborators,
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Impossible de charger "
                "la configuration."
            ),
        )


# ============================================================================
# GET FILIALES
# ============================================================================

@router.post("/get-filiales")
async def get_filiales_from_file(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Extracts filiales from a temporary uploaded Excel file.

    Maximum upload size: 500 MiB.
    """

    temp_input_path = os.path.join(
        settings.OUTPUT_DIR,
        f"temp_get_filiales_{uuid.uuid4().hex}.xlsx",
    )

    try:

        # ================================================================
        # SIZE-LIMITED UPLOAD
        # ================================================================

        save_upload_with_limit(
            upload_file=file,
            destination_path=temp_input_path,
        )

        # ================================================================
        # READ EXCEL
        # ================================================================

        df = pd.read_excel(
            temp_input_path,
            sheet_name="RUN+MON",
            engine="openpyxl",
        )

        if "Projet" not in df.columns:
            raise ValueError(
                "La colonne 'Projet' "
                "est absente du fichier."
            )

        filiales = (
            df["Projet"]
            .dropna()
            .astype(str)
            .str.split("_")
            .str[0]
            .unique()
        )

        filiales = sorted(
            [
                filial.strip()
                for filial in filiales
                if filial.strip()
            ]
        )

        return {
            "filiales": filiales,
        }

    except HTTPException:
        raise

    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    finally:

        if os.path.exists(
            temp_input_path
        ):
            os.remove(
                temp_input_path
            )


# ============================================================================
# CREATE UPLOAD SESSION
# ============================================================================

@router.post("/upload-session")
async def create_upload_session(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Creates an isolated upload session.

    Maximum upload size: 500 MiB.
    The session is linked to the authenticated user.
    """

    session_id = uuid.uuid4().hex

    sessions_dir = (
        create_session_directory()
    )

    session_directory = os.path.join(
        sessions_dir,
        session_id,
    )

    os.makedirs(
        session_directory,
        exist_ok=False,
    )

    stored_file_name = (
        "source.xlsx"
    )

    session_file_path = os.path.join(
        session_directory,
        stored_file_name,
    )

    try:

        # ================================================================
        # SIZE-LIMITED UPLOAD
        # ================================================================

        save_upload_with_limit(
            upload_file=file,
            destination_path=session_file_path,
        )

        # ================================================================
        # READ EXCEL
        # ================================================================

        df = pd.read_excel(
            session_file_path,
            sheet_name="RUN+MON",
            engine="openpyxl",
        )

        if "Projet" not in df.columns:
            raise ValueError(
                "La colonne 'Projet' "
                "est absente du fichier."
            )

        filiales = (
            df["Projet"]
            .dropna()
            .astype(str)
            .str.split("_")
            .str[0]
            .unique()
        )

        filiales = sorted(
            [
                filial.strip()
                for filial in filiales
                if filial.strip()
            ]
        )

        # ================================================================
        # SAVE OWNERSHIP METADATA
        # ================================================================

        create_session_metadata(
            session_directory=session_directory,
            session_id=session_id,
            current_user=current_user,
            original_file_name=(
                file.filename
                or "upload.xlsx"
            ),
            stored_file_name=stored_file_name,
        )

        return {
            "session_id": session_id,
            "file_name": (
                file.filename
                or "upload.xlsx"
            ),
            "filiales": filiales,
        }

    except HTTPException:
        if os.path.exists(
            session_directory
        ):
            shutil.rmtree(
                session_directory,
                ignore_errors=True,
            )
        raise

    except Exception as e:

        if os.path.exists(
            session_directory
        ):
            shutil.rmtree(
                session_directory,
                ignore_errors=True,
            )

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )


# ============================================================================
# ADD COLLABORATOR
# ============================================================================

@router.post("/collaborators")
def add_collaborator(
    payload: dict,
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Adds a collaborator to collaborators.json.
    """

    collab_file = (
        settings.COLLABORATORS_PATH
    )

    name = str(
        payload.get(
            "name",
            "",
        )
    ).strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail=(
                "Le nom du collaborateur "
                "est requis."
            ),
        )

    try:

        with open(
            collab_file,
            "r",
            encoding="utf-8",
        ) as f:
            collaborators = json.load(f)

        if not isinstance(
            collaborators,
            list,
        ):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Le fichier des collaborateurs "
                    "doit contenir une liste."
                ),
            )

        if name not in collaborators:

            collaborators.append(
                name
            )

            with open(
                collab_file,
                "w",
                encoding="utf-8",
            ) as f:
                json.dump(
                    collaborators,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

        return {
            "name": name,
            "collaborators": collaborators,
            "message": (
                "Collaborateur ajouté "
                "avec succès."
            ),
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de la sauvegarde "
                "du collaborateur."
            ),
        )


# ============================================================================
# DELETE COLLABORATOR
# ============================================================================

@router.delete(
    "/collaborators/{name}"
)
def delete_collaborator(
    name: str,
    current_user: User = Depends(
        get_current_user
    ),
):
    """
    Deletes a collaborator from collaborators.json.
    """

    collab_file = (
        settings.COLLABORATORS_PATH
    )

    name = name.strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail=(
                "Le nom du collaborateur "
                "est requis."
            ),
        )

    try:

        with open(
            collab_file,
            "r",
            encoding="utf-8",
        ) as f:
            collaborators = json.load(f)

        if not isinstance(
            collaborators,
            list,
        ):
            raise HTTPException(
                status_code=500,
                detail=(
                    "Le fichier des collaborateurs "
                    "doit contenir une liste."
                ),
            )

        if name not in collaborators:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Collaborateur introuvable."
                ),
            )

        collaborators.remove(
            name
        )

        with open(
            collab_file,
            "w",
            encoding="utf-8",
        ) as f:
            json.dump(
                collaborators,
                f,
                ensure_ascii=False,
                indent=2,
            )

        return {
            "name": name,
            "collaborators": collaborators,
            "message": (
                "Collaborateur supprimé "
                "avec succès."
            ),
        }

    except HTTPException:
        raise

    except Exception:
        raise HTTPException(
            status_code=500,
            detail=(
                "Erreur lors de la suppression."
            ),
        )


# ============================================================================
# SLA MAPPING MANAGEMENT (CRUD)
# ============================================================================

@router.get("/sla-mapping")
def get_sla_mapping(
    current_user: User = Depends(get_current_user),
):
    """
    Returns the current SLA mapping configuration from config/sla_mapping.json.
    """
    sla_file = settings.SLA_MAPPING_PATH
    try:
        with open(sla_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)
        return mapping
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la lecture du fichier SLA : {str(e)}",
        )


@router.post("/sla-mapping")
def add_sla_domain(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Adds a new sub-domain to a specific SLA category ('2', '5', or '15').
    """
    name = str(payload.get("name", "")).strip()
    sla = str(payload.get("sla", "")).strip()

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Le nom du sous-domaine est requis.",
        )

    if sla not in ("2", "5", "15"):
        raise HTTPException(
            status_code=400,
            detail="La catégorie SLA doit être 2, 5 ou 15 jours.",
        )

    sla_file = settings.SLA_MAPPING_PATH

    try:
        with open(sla_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        for cat in ("2", "5", "15"):
            if cat not in mapping or not isinstance(mapping[cat], list):
                mapping[cat] = []

        # Check if already in target category
        if name in mapping[sla]:
            return {
                "message": f"Le sous-domaine '{name}' existe déjà dans la catégorie {sla}j.",
                "sla_mapping": mapping,
            }

        # Remove from any other category if it was previously mapped elsewhere
        for cat in ("2", "5", "15"):
            if cat != sla and name in mapping[cat]:
                mapping[cat].remove(name)

        mapping[sla].append(name)

        with open(sla_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        return {
            "name": name,
            "sla": sla,
            "message": f"Sous-domaine '{name}' ajouté avec succès dans la catégorie {sla}j.",
            "sla_mapping": mapping,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la sauvegarde du sous-domaine : {str(e)}",
        )


@router.put("/sla-mapping")
def update_sla_domain(
    payload: dict,
    current_user: User = Depends(get_current_user),
):
    """
    Updates an existing sub-domain (renaming and/or changing SLA category).
    """
    old_name = str(payload.get("old_name", "")).strip()
    new_name = str(payload.get("new_name", "")).strip()
    old_sla = str(payload.get("old_sla", "")).strip()
    new_sla = str(payload.get("new_sla", "")).strip()

    if not old_name or not new_name:
        raise HTTPException(
            status_code=400,
            detail="L'ancien et le nouveau nom du sous-domaine sont requis.",
        )

    if old_sla not in ("2", "5", "15") or new_sla not in ("2", "5", "15"):
        raise HTTPException(
            status_code=400,
            detail="Les catégories SLA doivent être 2, 5 ou 15 jours.",
        )

    sla_file = settings.SLA_MAPPING_PATH

    try:
        with open(sla_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        for cat in ("2", "5", "15"):
            if cat not in mapping or not isinstance(mapping[cat], list):
                mapping[cat] = []

        if old_name not in mapping[old_sla]:
            raise HTTPException(
                status_code=404,
                detail=f"Sous-domaine '{old_name}' introuvable dans la catégorie {old_sla}j.",
            )

        # Remove old entry
        mapping[old_sla].remove(old_name)

        # If changing categories, ensure it doesn't leave ghosts in other categories
        for cat in ("2", "5", "15"):
            if new_name in mapping[cat]:
                mapping[cat].remove(new_name)

        mapping[new_sla].append(new_name)

        with open(sla_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        return {
            "old_name": old_name,
            "new_name": new_name,
            "new_sla": new_sla,
            "message": f"Sous-domaine mis à jour avec succès vers {new_sla}j.",
            "sla_mapping": mapping,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la mise à jour du sous-domaine : {str(e)}",
        )


@router.delete("/sla-mapping/{sla}/{name}")
def delete_sla_domain(
    sla: str,
    name: str,
    current_user: User = Depends(get_current_user),
):
    """
    Deletes a sub-domain from a specific SLA category.
    """
    sla = sla.strip()
    name = name.strip()

    if sla not in ("2", "5", "15"):
        raise HTTPException(
            status_code=400,
            detail="La catégorie SLA doit être 2, 5 ou 15 jours.",
        )

    if not name:
        raise HTTPException(
            status_code=400,
            detail="Le nom du sous-domaine est requis.",
        )

    sla_file = settings.SLA_MAPPING_PATH

    try:
        with open(sla_file, "r", encoding="utf-8") as f:
            mapping = json.load(f)

        if sla not in mapping or name not in mapping[sla]:
            raise HTTPException(
                status_code=404,
                detail=f"Sous-domaine '{name}' introuvable dans la catégorie {sla}j.",
            )

        mapping[sla].remove(name)

        with open(sla_file, "w", encoding="utf-8") as f:
            json.dump(mapping, f, ensure_ascii=False, indent=2)

        return {
            "name": name,
            "sla": sla,
            "message": f"Sous-domaine '{name}' supprimé avec succès de la catégorie {sla}j.",
            "sla_mapping": mapping,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Erreur lors de la suppression du sous-domaine : {str(e)}",
        )