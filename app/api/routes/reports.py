import os
import json
import uuid
import shutil
import traceback

from datetime import datetime, timezone

from fastapi import (
    APIRouter,
    Depends,
    UploadFile,
    File,
    Form,
    HTTPException,
)

from fastapi.responses import FileResponse

from app.api.dependencies import (
    get_current_user,
    User,
)

from app.api.routes.config import (
    get_owned_session,
    save_upload_with_limit,
)

try:
    from app.core.config import settings
except ModuleNotFoundError:
    from core.config import settings

from app.services.kpi_service import (
    generate_report,
)


router = APIRouter(
    prefix="/api",
    tags=["Reports"],
)


# ============================================================================
# JOB HELPERS
# ============================================================================

def create_job_directory():
    """
    Creates a unique directory for one generated Excel report.
    """

    job_id = uuid.uuid4().hex

    jobs_root = os.path.join(
        settings.OUTPUT_DIR,
        "jobs",
    )

    os.makedirs(
        jobs_root,
        exist_ok=True,
    )

    job_directory = os.path.join(
        jobs_root,
        job_id,
    )

    os.makedirs(
        job_directory,
        exist_ok=False,
    )

    return (
        job_id,
        job_directory,
    )


def write_job_metadata(
    job_directory: str,
    job_id: str,
    current_user: User,
    report_type: str,
    start_date: str,
    end_date: str,
    file_name: str,
):
    """
    Stores traceability information for the generated report.
    """

    metadata_path = os.path.join(
        job_directory,
        "metadata.json",
    )

    metadata = {
        "job_id": job_id,
        "username": current_user.username,
        "type": report_type,
        "created_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "start_date": start_date,
        "end_date": end_date,
        "file_name": file_name,
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


def is_valid_job_id(
    job_id: str,
) -> bool:
    """
    Job IDs are generated with uuid.uuid4().hex.
    """

    if not isinstance(
        job_id,
        str,
    ):
        return False

    if len(job_id) != 32:
        return False

    return all(
        char in "0123456789abcdefABCDEF"
        for char in job_id
    )


# ============================================================================
# GENERATE REPORT
# ============================================================================

@router.post("/generate-report")
async def process_report(
    file: UploadFile = File(None),
    session_id: str = Form(None),
    start_date: str = Form(...),
    end_date: str = Form(...),
    date_column: str = Form(...),
    sla_groups: str = Form(...),
    collaborators: str = Form(...),
    current_user: User = Depends(
        get_current_user
    ),
):

    temp_input_path = None
    is_temp_upload = False
    job_directory = None

    try:

        # ====================================================================
        # INPUT FILE
        # ====================================================================

        if file is not None:

            temp_input_path = os.path.join(
                settings.OUTPUT_DIR,
                f"temp_report_{uuid.uuid4().hex}.xlsx",
            )

            # 500 MiB limit is enforced while reading.
            save_upload_with_limit(
                upload_file=file,
                destination_path=temp_input_path,
            )

            is_temp_upload = True

        elif session_id:

            # Session ownership is verified here.
            temp_input_path, _session_metadata = (
                get_owned_session(
                    session_id,
                    current_user,
                )
            )

        else:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Fichier ou ID de session requis."
                ),
            )

        # ====================================================================
        # CREATE UNIQUE JOB
        # ====================================================================

        job_id, job_directory = (
            create_job_directory()
        )

        report_path = os.path.join(
            job_directory,
            "report.xlsx",
        )

        # ====================================================================
        # PARAMETERS
        # ====================================================================

        try:

            sla_list = json.loads(
                sla_groups
            )

            collab_list = json.loads(
                collaborators
            )

        except json.JSONDecodeError:

            raise HTTPException(
                status_code=400,
                detail=(
                    "Paramètres SLA/collaborateurs "
                    "invalides."
                ),
            )

        # ====================================================================
        # GENERATE EXCEL
        # ====================================================================

        kpi_stats, output_path = (
            generate_report(
                file_path=temp_input_path,
                start_date=start_date,
                end_date=end_date,
                date_column=date_column,
                sla_groups=sla_list,
                collaborators=collab_list,
                output_path=report_path,
            )
        )

        # ====================================================================
        # TRACEABILITY
        # ====================================================================

        write_job_metadata(
            job_directory=job_directory,
            job_id=job_id,
            current_user=current_user,
            report_type="excel",
            start_date=start_date,
            end_date=end_date,
            file_name="report.xlsx",
        )

        download_url = (
            f"/api/download/{job_id}"
        )

        return {
            "stats": kpi_stats,
            "job_id": job_id,
            "download_url": download_url,
        }

    except HTTPException:
        raise

    except Exception as e:

        traceback.print_exc()

        if (
            job_directory
            and os.path.exists(
                job_directory
            )
        ):
            shutil.rmtree(
                job_directory,
                ignore_errors=True,
            )

        raise HTTPException(
            status_code=400,
            detail=str(e),
        )

    finally:

        if (
            is_temp_upload
            and temp_input_path
            and os.path.exists(
                temp_input_path
            )
        ):
            os.remove(
                temp_input_path
            )


# ============================================================================
# DOWNLOAD REPORT
# ============================================================================

@router.get(
    "/download/{job_id}"
)
def download_report(
    job_id: str,
    current_user: User = Depends(
        get_current_user
    ),
):

    if not is_valid_job_id(
        job_id
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Identifiant de job invalide."
            ),
        )

    job_directory = os.path.join(
        settings.OUTPUT_DIR,
        "jobs",
        job_id,
    )

    metadata_path = os.path.join(
        job_directory,
        "metadata.json",
    )

    report_path = os.path.join(
        job_directory,
        "report.xlsx",
    )

    if not os.path.exists(
        metadata_path
    ):
        raise HTTPException(
            status_code=404,
            detail="Rapport introuvable.",
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
                "Métadonnées du rapport invalides."
            ),
        )

    if (
        metadata.get("username")
        != current_user.username
    ):
        raise HTTPException(
            status_code=403,
            detail="Accès interdit.",
        )

    if not os.path.exists(
        report_path
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Fichier du rapport "
                "introuvable."
            ),
        )

    start_date = metadata.get(
        "start_date",
        "",
    )

    end_date = metadata.get(
        "end_date",
        "",
    )

    return FileResponse(
        path=report_path,
        filename=(
            f"SLA du "
            f"{start_date} "
            f"au "
            f"{end_date}.xlsx"
        ),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),
    )