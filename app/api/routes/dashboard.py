import os
import json
import uuid
import shutil
import traceback

from datetime import datetime, timezone

from typing import List

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

from app.services.dashboard_service import (
    generate_dashboard,
)


router = APIRouter(
    prefix="/api",
    tags=["Dashboard"],
)


# ============================================================================
# JOB HELPERS
# ============================================================================

def create_job_directory():
    """
    Creates a unique directory for one PowerPoint dashboard job.
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


def write_dashboard_metadata(
    job_directory: str,
    job_id: str,
    current_user: User,
    start_date: str,
    end_date: str,
    filiale: str,
):
    """
    Stores traceability information for the generated dashboard.
    """

    metadata_path = os.path.join(
        job_directory,
        "metadata.json",
    )

    metadata = {
        "job_id": job_id,
        "username": current_user.username,
        "type": "powerpoint",
        "created_at": (
            datetime.now(
                timezone.utc
            ).isoformat()
        ),
        "start_date": start_date,
        "end_date": end_date,
        "filiale": filiale,
        "file_name": "dashboard.pptx",
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
# GENERATE DASHBOARD
# ============================================================================

@router.post("/generate-ppt")
async def process_dashboard(
    file: UploadFile = File(None),
    session_id: str = Form(None),
    start_date: str = Form(...),
    end_date: str = Form(...),
    filiales: List[str] = Form(...),
    current_user: User = Depends(
        get_current_user
    ),
):

    temp_input_path = None
    is_temp_upload = False

    created_job_directories = []

    try:

        # ====================================================================
        # INPUT FILE
        # ====================================================================

        if file is not None:

            temp_input_path = os.path.join(
                settings.OUTPUT_DIR,
                f"temp_dashboard_{uuid.uuid4().hex}.xlsx",
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
        # GENERATE ONE JOB PER FILIALE
        # ====================================================================

        results = []

        for filiale in filiales:

            job_id, job_directory = (
                create_job_directory()
            )

            created_job_directories.append(
                job_directory
            )

            dashboard_path = os.path.join(
                job_directory,
                "dashboard.pptx",
            )

            # ================================================================
            # GENERATE DASHBOARD
            # ================================================================

            kpi_stats, output_path = (
                generate_dashboard(
                    file_path=temp_input_path,
                    start_date=start_date,
                    end_date=end_date,
                    filiale=filiale,
                    output_path=dashboard_path,
                )
            )

            # ================================================================
            # TRACEABILITY
            # ================================================================

            write_dashboard_metadata(
                job_directory=job_directory,
                job_id=job_id,
                current_user=current_user,
                start_date=start_date,
                end_date=end_date,
                filiale=filiale,
            )

            download_url = (
                f"/api/download-dashboard/"
                f"{job_id}"
            )

            results.append({
                "filiale": filiale,
                "stats": kpi_stats,
                "job_id": job_id,
                "download_url": download_url,
            })

        return {
            "results": results,
        }

    except HTTPException:
        raise

    except Exception as e:

        traceback.print_exc()

        for job_directory in (
            created_job_directories
        ):

            if os.path.exists(
                job_directory
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
# DOWNLOAD DASHBOARD
# ============================================================================

@router.get(
    "/download-dashboard/{job_id}"
)
def download_dashboard(
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

    dashboard_path = os.path.join(
        job_directory,
        "dashboard.pptx",
    )

    if not os.path.exists(
        metadata_path
    ):
        raise HTTPException(
            status_code=404,
            detail="Dashboard introuvable.",
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
                "Métadonnées du dashboard invalides."
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
        dashboard_path
    ):
        raise HTTPException(
            status_code=404,
            detail=(
                "Fichier du dashboard "
                "introuvable."
            ),
        )

    filiale = metadata.get(
        "filiale",
        "Dashboard",
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
        path=dashboard_path,
        filename=(
            f"Dashboard {filiale} "
            f"du {start_date} "
            f"au {end_date}.pptx"
        ),
        media_type=(
            "application/vnd.openxmlformats-officedocument."
            "presentationml.presentation"
        ),
    )