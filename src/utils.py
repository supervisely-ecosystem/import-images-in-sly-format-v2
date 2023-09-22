import os
import supervisely as sly
from supervisely import Project, Dataset, OpenMode
from supervisely.io.fs import list_dir_recursively, get_file_name_with_ext, silent_remove

HELPER_MD = """
## Input files structure

**Key features:**
- You can upload a directory or an archive.
- If you are uploading an archive, it must contain a single top-level directory.
- Subdirectories will define dataset names.

ℹ️ You can download the archive with data example [here](https://github.com/supervisely-ecosystem/import-images-in-sly-format/files/12537201/robots_project.zip).

**Project directory structure:**

```
📂my_project
 ┣ 📂ds1
 ┃ ┣ 📂ann
 ┃ ┃ ┣ 📜image_0748.jpeg.json
 ┃ ┃ ┣ 📜...
 ┃ ┃ ┗ 📜image_8144.jpeg.json
 ┃ ┗ 📂img
 ┃ ┃ ┣ 🖼️image_0748.jpeg
 ┃ ┃ ┣ 🖼️...
 ┃ ┃ ┗ 🖼️image_8144.jpeg
 ┣ 📂ds2
 ┃ ┣ 📂ann
 ┃ ┃ ┣ 📜image_9545.jpeg.json
 ┃ ┃ ┣ 📜...
 ┃ ┃ ┗ 📜image_9999.jpeg.json
 ┃ ┗ 📂img
 ┃ ┃ ┣ 🖼️image_9545.jpeg
 ┃ ┃ ┣ 🖼️...
 ┃ ┃ ┗ 🖼️image_9999.jpeg
 ┗ 📜meta.json
```

**Archive with project directory structure:**
```
📦my_project_archive.zip
┗ 📂my_project
  ┣ 📂ds1
  ┃ ┣ 📂ann
  ┃ ┃ ┣ 📜image_0748.jpeg.json
  ┃ ┃ ┣ 📜...
  ┃ ┃ ┗ 📜image_8144.jpeg.json
  ┃ ┗ 📂img
  ┃ ┃ ┣ 🖼️image_0748.jpeg
  ┃ ┃ ┣ 🖼️...
  ┃ ┃ ┗ 🖼️image_8144.jpeg
  ┣ 📂ds2
  ┃ ┣ 📂ann
  ┃ ┃ ┣ 📜image_9545.jpeg.json
  ┃ ┃ ┣ 📜...
  ┃ ┃ ┗ 📜image_9999.jpeg.json
  ┃ ┗ 📂img
  ┃ ┃ ┣ 🖼️image_9545.jpeg
  ┃ ┃ ┣ 🖼️...
  ┃ ┃ ┗ 🖼️image_9999.jpeg
  ┗ 📜meta.json
```

As a result, we will get project with 2 datasets named: `ds1` and `ds2`.
"""

ERROR_HELPER_TEXT = (
    "Go to step 1 and press 'Restart' button to reselect data. "
    "Please see format structure for more details on format."
    )


def validate(directory: str) -> Project:
    dir_content = os.listdir(directory)
    if len(dir_content) != 1:
        raise RuntimeError(
            f"Root directory must contain only one directory or archive. " f"{ERROR_HELPER_TEXT}"
        )

    project = os.path.join(directory, dir_content[0])
    if os.path.isfile(project):
        sly.fs.unpack_archive(project, directory)
        silent_remove(project)
        dir_content = os.listdir(directory)
        if len(dir_content) != 1:
            raise RuntimeError(
                f"Archive must contain only one top-level directory. " f"{ERROR_HELPER_TEXT}"
            )
        project = os.path.join(directory, dir_content[0])

    projects = []
    projects_paths = []
    parent_directories = []
    paths = list_dir_recursively(directory)
    if len(paths) == 0:
        raise RuntimeError(f"Root directory is empty. {ERROR_HELPER_TEXT}")

    has_meta = False
    for path in paths:
        if get_file_name_with_ext(path) == "meta.json":
            has_meta = True
            parent_dir = os.path.dirname(path)
            project_dir = os.path.join(directory, parent_dir)
            try:
                project = Project(project_dir, OpenMode.READ)
                projects.append(project)
                projects_paths.append(project_dir)
                parent_directories.append(parent_dir)
            except Exception:
                pass

    if not has_meta:
        raise RuntimeError(f"meta.json is not found. {ERROR_HELPER_TEXT}")

    if len(projects) == 0:
        raise RuntimeError(
            f"Root directory does not contain any valid projects. " f"{ERROR_HELPER_TEXT}"
        )
    if len(projects) > 1:
        raise RuntimeError(
            f"Root directory contains more than one project: '{parent_directories}'. "
            f"{ERROR_HELPER_TEXT}"
        )

    project = projects[0]
    project_path = projects_paths[0]
    parent_dir = parent_directories[0]

    sly.logger.info(f"Validating project in directory '{parent_dir}'")
    # Check if meta.json exists in the project directory
    meta_json_path = os.path.join(project_path, "meta.json")
    if not os.path.exists(meta_json_path):
        raise RuntimeError(f"meta.json is missing in '{parent_dir}'. {ERROR_HELPER_TEXT}")

    # Check for dataset folders in the project directory
    dataset_folders = [
        f for f in os.listdir(project_path) if os.path.isdir(os.path.join(project_path, f))
    ]

    if len(dataset_folders) == 0:
        raise RuntimeError(
            f"No dataset folders found in the project directory: '{parent_dir}'. "
            f"{ERROR_HELPER_TEXT}"
        )

    # Iterate through each dataset folder
    for dataset_folder in dataset_folders:
        dataset_path = os.path.join(project_path, dataset_folder)
        try:
            dataset = Dataset(dataset_folder, OpenMode.READ)
            sly.logger.info(f"Dataset: '{dataset.name}' is valid.")
        except RuntimeError as e:
            raise RuntimeError(f"{str(e)}. {ERROR_HELPER_TEXT}") from e

    sly.logger.info(f"Project in directory '{parent_dir}' is valid. Start import.")
    return project
