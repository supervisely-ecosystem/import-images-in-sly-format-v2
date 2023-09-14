import os
import supervisely as sly
from dotenv import load_dotenv
from supervisely.project.project import find_project_dirs

# load ENV variables for debug, has no effect in production
if sly.is_production():
    load_dotenv("advanced.env")
else:
    load_dotenv("local.env")
load_dotenv(os.path.expanduser("~/supervisely.env"))


def validate_project(path):
    project_dirs = list(find_project_dirs(path))
    if len(project_dirs) == 0:
        try:
            sly.Project(path, sly.OpenMode.READ)
        except:
            raise RuntimeError(
                ("Project is not valid. " "Select another directory or archive in file selector.")
            )


class MyImport(sly.app.Import):
    def process(self, context: sly.app.Import.Context):
        # create api object to communicate with Supervisely Server
        api = sly.Api.from_env()

        validate_project(context.path)
        project_id, project_name = sly.upload_project(
            dir=context.path,
            api=api,
            workspace_id=context.workspace_id,
            name=context.project_name or "my project",
        )

        # clean local data dir after successful import
        sly.fs.remove_dir(context.path)
        project = api.project.get_info_by_id(project_id)
        return project


app = MyImport()
app.run()
