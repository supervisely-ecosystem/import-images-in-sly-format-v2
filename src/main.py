import os
import supervisely as sly
from dotenv import load_dotenv
from supervisely.project.project import find_project_dirs
from supervisely.io.fs import list_dir_recursively, get_file_name_with_ext

# load ENV variables for debug, has no effect in production
if sly.is_production():
    load_dotenv("advanced.env")
else:
    load_dotenv("local.env")
load_dotenv(os.path.expanduser("~/supervisely.env"))


def validate_project(directory):
    # directories = find_project_dirs(directory)
    directories = []
    paths = list_dir_recursively(directory)
    for path in paths:
        if get_file_name_with_ext(path) == "meta.json":
            parent_dir = os.path.dirname(path)
            project_dir = os.path.join(directory, parent_dir)
            try:
                sly.Project(project_dir, sly.OpenMode.READ)
                directories.append(project_dir)
            except Exception:
                pass

    if len(directories) == 0:
        raise RuntimeError(f"Directory {directory} does not contain any projects")
    if len(directories) > 1:
        raise RuntimeError(f"Directory {directory} contains more than one project")

    directory = directories[0]
    sly.logger.info(f"Validating project in directory '{directory}'")
    # Check if meta.json exists in the project directory
    meta_json_path = os.path.join(directory, "meta.json")
    if not os.path.exists(meta_json_path):
        raise RuntimeError(f"meta.json is missing in {directory}")

    # Check for dataset folders in the project directory
    dataset_folders = [
        f for f in os.listdir(directory) if os.path.isdir(os.path.join(directory, f))
    ]

    if len(dataset_folders) == 0:
        raise RuntimeError("No dataset folders found in the project directory")

    # Iterate through each dataset folder
    for dataset_folder in dataset_folders:
        dataset_path = os.path.join(directory, dataset_folder)
        ann_path = os.path.join(dataset_path, "ann")
        img_path = os.path.join(dataset_path, "img")

        # Check if ann and img folders exist in the dataset folder
        if not os.path.exists(img_path):
            raise RuntimeError(f"Dataset {dataset_folder} is missing 'img' folder")
        if not os.path.exists(ann_path):
            raise RuntimeError(f"Dataset {dataset_folder} is missing 'ann' folder")

        # Check for annotation files in the 'ann' folder
        ann_files = [f for f in os.listdir(ann_path) if f.endswith(".json")]
        img_files = [f for f in os.listdir(img_path) if not f.endswith(".json")]

        # Check if annotation files have corresponding image files
        for ann_file in ann_files:
            img_file = os.path.splitext(ann_file)[0]
            if img_file not in img_files:
                raise RuntimeError(
                    f"Annotation file {ann_file} does not have a corresponding image file"
                )
        sly.logger.info(f"Project in directory '{directory}' is valid. Start import.")


class MyImport(sly.app.Import):
    def process(self, context: sly.app.Import.Context):
        # create api object to communicate with Supervisely Server
        api = sly.Api.from_env()

        validate_project(context.path)
        # progress = context.progress(message="Uploading Project")
        project_id, project_name = sly.upload_project(
            dir=context.path,
            api=api,
            workspace_id=context.workspace_id,
            name=context.project_name or "my project",
            progress_cb=context.progress,
        )

        # clean local data dir after successful import
        sly.fs.remove_dir(context.path)
        project = api.project.get_info_by_id(project_id)
        return project


app = MyImport(
    allowed_project_types=[sly.ProjectType.IMAGES],
    allowed_destination_options=[sly.app.Import.Destination.NEW_PROJECT],
)
app.run()
