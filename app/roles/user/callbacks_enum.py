# 39 symbols is the limit for callback name, as ObjectId comes next (and telegram has 64bits callback name limit)
class Callbacks:
    cancel_tag_manage_callback = "on_cancel_tag_manage_callback"
    cancel_primary_action_callback = "on_cancel_primary_callback_with_deletion"
    cancel_tag_action_callback = "on_cancel_tag_action_callback"
    tag_delete_callback = "on_tag_delete_callback"
    tag_edit_callback = "on_tag_edit_callback"
    tag_create_callback = "on_tag_create_callback"
    tag_clicked_manage_callback = "tag_clicked_manage_callback"
    tag_clicked_in_recording_mode_callback = "on_tag_clicked_in_recording_mode_callback"
    cancel_tag_naming_callback = "on_cancel_tag_naming_callback"
