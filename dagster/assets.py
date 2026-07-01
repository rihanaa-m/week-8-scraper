import os
from pathlib import Path
from datetime import datetime
import subprocess
from dagster import asset, AssetExecutionContext, Definitions
from dagster.utils import file_relative_path


@asset
def telegram_scrape_data(context: AssetExecutionContext) -> str:
    """
    Asset: Scrape Telegram channels and download images.
    """
    context.log.info("Starting Telegram data scrape...")
    
    # Run the scraper script
    scraper_path = Path(__file__).parent.parent / "src" / "scraper.py"
    result = subprocess.run(
        ["python", str(scraper_path)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        context.log.error(f"Scraper failed: {result.stderr}")
        raise Exception(f"Scraper failed with return code {result.returncode}")
    
    context.log.info("Telegram data scrape completed successfully")
    return datetime.now().isoformat()


@asset(deps=[telegram_scrape_data])
def load_raw_data(context: AssetExecutionContext) -> str:
    """
    Asset: Load raw JSON data into PostgreSQL database.
    """
    context.log.info("Loading raw data into PostgreSQL...")
    
    # Run the load script
    load_script = Path(__file__).parent.parent / "scripts" / "load_raw_data.py"
    result = subprocess.run(
        ["python", str(load_script)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        context.log.error(f"Load script failed: {result.stderr}")
        raise Exception(f"Load script failed with return code {result.returncode}")
    
    context.log.info("Raw data loaded successfully")
    return datetime.now().isoformat()


@asset(deps=[load_raw_data])
def dbt_transform(context: AssetExecutionContext) -> str:
    """
    Asset: Run dbt transformations to build star schema.
    """
    context.log.info("Running dbt transformations...")
    
    # Change to dbt project directory
    dbt_dir = Path(__file__).parent.parent / "medical_warehouse"
    
    # Run dbt run
    result = subprocess.run(
        ["dbt", "run"],
        cwd=str(dbt_dir),
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        context.log.error(f"dbt run failed: {result.stderr}")
        raise Exception(f"dbt run failed with return code {result.returncode}")
    
    context.log.info("dbt transformations completed successfully")
    return datetime.now().isoformat()


@asset(deps=[telegram_scrape_data])
def yolo_object_detection(context: AssetExecutionContext) -> str:
    """
    Asset: Run YOLO object detection on downloaded images.
    """
    context.log.info("Starting YOLO object detection...")
    
    # Run YOLO detection script
    yolo_script = Path(__file__).parent.parent / "src" / "yolo_detect.py"
    result = subprocess.run(
        ["python", str(yolo_script)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        context.log.error(f"YOLO detection failed: {result.stderr}")
        raise Exception(f"YOLO detection failed with return code {result.returncode}")
    
    context.log.info("YOLO object detection completed successfully")
    return datetime.now().isoformat()


@asset(deps=[yolo_object_detection])
def load_yolo_results(context: AssetExecutionContext) -> str:
    """
    Asset: Load YOLO detection results into database.
    """
    context.log.info("Loading YOLO results into database...")
    
    # Run YOLO results load script
    load_script = Path(__file__).parent.parent / "scripts" / "load_yolo_results.py"
    result = subprocess.run(
        ["python", str(load_script)],
        capture_output=True,
        text=True
    )
    
    if result.returncode != 0:
        context.log.error(f"YOLO results load failed: {result.stderr}")
        raise Exception(f"YOLO results load failed with return code {result.returncode}")
    
    context.log.info("YOLO results loaded successfully")
    return datetime.now().isoformat()


@asset(deps=[dbt_transform, load_yolo_results])
def data_pipeline_complete(context: AssetExecutionContext) -> str:
    """
    Asset: Final asset indicating complete data pipeline execution.
    """
    context.log.info("Data pipeline execution completed successfully")
    return datetime.now().isoformat()


# Define the Dagster Definitions
defs = Definitions(
    assets=[
        telegram_scrape_data,
        load_raw_data,
        dbt_transform,
        yolo_object_detection,
        load_yolo_results,
        data_pipeline_complete
    ]
)
