# 39 symbols is the limit for callback name, because ObjectId comes next (and telegram has 64bits callback name limit)
class Callbacks:
    get_recording_by_link_callback = "get_recording_by_link"
    get_recording_by_tag_callback = "get_recording_by_tag"
    cancel_deletion = "confirm_delete"
    confirm_deletion = "cancel_delete"
    cancel_tag_manage_callback = "on_cancel_tag_manage"
    cancel_primary_action_callback = "on_cancel_primary"
    cancel_tag_action_callback = "on_cancel_tag_action"
    cancel_tag_naming_callback = "on_cancel_tag_naming"
    return_back_from_archived_callback = "on_return_from_archived_list"
    return_back_from_archived_tag_actions_callback = "on_return_from_archived_actions"
    tag_delete_callback = "on_tag_delete"
    tag_edit_callback = "on_tag_edit"
    tag_create_callback = "on_tag_create"
    tag_clicked_manage_callback = "on_tag_clicked_manage"
    tag_clicked_in_recording_mode_callback = "on_tag_clicked_in_recording"
    tag_archive_callback = "on_tag_archive"
    archived_tag_clicked_manage_callback = "on_archived_tag_clicked_in_manage"
    unarchive_tag_clicked_callback = "on_unarchive_tag_clicked_in_manage"
    show_archived_in_manage_mode = "on_show_archive_in_manage"
    add_admin_callback = "on_add_admin"
    admin_delete_callback = "on_admin_delete"
    return_to_admin_list_callback = "on_return_to_admin_list"
