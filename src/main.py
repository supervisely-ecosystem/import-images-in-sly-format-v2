from os.path import join, expanduser
import supervisely as sly
from dotenv import load_dotenv
from supervisely.app.widgets import Widget, Markdown
import src.utils as utils

# load ENV variables for debug, has no effect in production
if sly.is_production():
    load_dotenv("advanced.env")
else:
    load_dotenv("local.env")
load_dotenv(expanduser("~/supervisely.env"))


class MyImport(sly.app.Import):
    def show_format_structure(self) -> Widget or str:
        return Markdown(utils.HELPER_MD)

    def process(self, context: sly.app.Import.Context):
        # create api object to communicate with Supervisely Server
        api = sly.Api.from_env()

        project = utils.validate(context.path)
        project_path = join(project.parent_dir, project.name)

        progress = context.progress(
            message=f"Uploading project: '{context.project_name}'",
            total=project.total_items * 2,  # img + ann
        )
        project_id, _ = sly.upload_project(
            dir=project_path,
            api=api,
            workspace_id=context.workspace_id,
            project_name=context.project_name,
            progress_cb=progress.update,
        )

        # clean local data dir after successful import
        sly.fs.remove_dir(context.path)
        return project_id


app = MyImport(
    allowed_project_types=[sly.ProjectType.IMAGES],
    allowed_destination_options=[sly.app.Import.Destination.NEW_PROJECT],
)
app.run()
