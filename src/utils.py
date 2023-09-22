import contextlib
from os import listdir
from os.path import dirname, exists, isdir, isfile, join

import supervisely as sly
from supervisely import Dataset, OpenMode, Project, logger
from supervisely.io.fs import (
    get_file_name_with_ext,
    list_dir_recursively,
    list_files,
    silent_remove,
    unpack_archive,
)

HELPER_MD = """
## Input files structure

**Key features:**
- You can import a directory or an archive.
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
    "<br><br>"
    "⚠️Please, see format structure for more details on format.<br>"
    "⚠️Go to step 1 and press 'Restart' button to reselect data."
)


def validate(directory: str) -> Project:
    dir_content = listdir(directory)
    if len(dir_content) != 1:
        raise RuntimeError(
            f"Root directory must contain only one directory or archive. " f"{ERROR_HELPER_TEXT}"
        )

    project = join(directory, dir_content[0])
    if isfile(project):
        unpack_archive(project, directory)
        silent_remove(project)
        dir_content = listdir(directory)
        if len(dir_content) != 1:
            raise RuntimeError(
                f"Archive must contain only one top-level directory. " f"{ERROR_HELPER_TEXT}"
            )
        project = join(directory, dir_content[0])

    projects = []
    projects_paths = []
    parent_directories = []
    paths = list_dir_recursively(directory)
    if len(paths) == 0:
        raise RuntimeError(f"Root directory is empty.{ERROR_HELPER_TEXT}")

    has_meta = False
    for path in paths:
        if get_file_name_with_ext(path) == "meta.json":
            has_meta = True
            parent_dir = dirname(path)
            project_dir = join(directory, parent_dir)
            with contextlib.suppress(Exception):
                project = Project(project_dir, OpenMode.READ)
                projects.append(project)
                projects_paths.append(project_dir)
                parent_directories.append(parent_dir)

    if not has_meta:
        raise RuntimeError(f"meta.json is not found.{ERROR_HELPER_TEXT}")

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

    logger.info(f"Validating project in directory '{parent_dir}'")
    # Check if meta.json exists in the project directory
    meta_json_path = join(project_path, "meta.json")
    if not exists(meta_json_path):
        raise RuntimeError(f"meta.json is missing in '{parent_dir}'.{ERROR_HELPER_TEXT}")

    # Check for dataset folders in the project directory
    dataset_folders = [f for f in listdir(project_path) if isdir(join(project_path, f))]

    if len(dataset_folders) == 0:
        raise RuntimeError(
            f"No dataset folders found in the project directory: '{parent_dir}'. "
            f"{ERROR_HELPER_TEXT}"
        )

    # Iterate through each dataset folder
    for dataset_folder in dataset_folders:
        dataset_path = join(project_path, dataset_folder)
        try:
            dataset = Dataset(dataset_path, OpenMode.READ)
        except Exception as e:
            modified_error = f"{str(e)}.{ERROR_HELPER_TEXT}"
            raise RuntimeError(modified_error)

        if len(list_files(dataset.img_dir)) == 0:
            raise RuntimeError(
                f"Dataset '{dataset.name}' does not contain any images. " f"{ERROR_HELPER_TEXT}"
            )
        logger.info(f"Dataset: '{dataset.name}' is valid.")

    logger.info(f"Project in directory '{parent_dir}' is valid. Start import.")
    return project
