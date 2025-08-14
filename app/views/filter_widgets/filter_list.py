import streamlit as st

from classes.session import Session
from views.filter_widgets.no_filter_placeholder import no_filter_placeholder_widget


def sidebar_widgets():
    session: Session = st.session_state["session"]
    fc = session.filter_container

    if st.button(
        "Create Filter",
        use_container_width=True,
        type="primary",
        icon=":material/add:",
    ):
        fc.set_mode("edit")
        st.rerun()


@st.dialog("Confirm Deletion")
def delete_confirmation_dialog(filter_id: str):
    session: Session = st.session_state["session"]
    fc = session.filter_container

    filter_obj = fc.filters[filter_id]

    if filter_obj.name:
        st.write(f"Delete Filter `{filter_obj.name}` ?")
    else:
        st.write(f"Delete Filter `Filter #{filter_id}` ?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Delete", type="primary", use_container_width=True):
            fc.remove_filter(filter_id)
            st.rerun()
    with col2:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.rerun()


def filter_list():
    session: Session = st.session_state["session"]
    fc = session.filter_container

    st.title("Filters")

    if not fc.filters:
        no_filter_placeholder_widget()
        return

    with st.sidebar:
        sidebar_widgets()

    for filter_id, filter_obj in fc.filters.items():
        with st.container(key=f"filter_{filter_id}_container", border=True):
            col1, col2 = st.columns([6, 1], vertical_alignment="center", gap="medium")

            with col1:
                st.subheader(filter_obj.pretty_name)
                st.code(filter_obj.query, language="python")

            with col2:
                _, toggle_container, _ = st.columns([1, 9, 1])
                col21, col22, col23 = st.columns(3)

                use_container_width = True

                col21.button(
                    label="",
                    key=f"filter_{filter_id}_edit_btn",
                    type="primary",
                    icon=":material/edit:",
                    use_container_width=use_container_width,
                    on_click=fc.set_mode,
                    args=("edit", filter_id),
                    help="Edit",
                )

                col22.button(
                    label="",
                    key=f"filter_{filter_id}_create_dupicate_btn",
                    type="primary",
                    icon=":material/content_copy:",
                    use_container_width=use_container_width,
                    on_click=fc.duplicate_filter,
                    args=(filter_id,),
                    help="Create Duplicate",
                )

                col23.button(
                    label="",
                    key=f"filter_{filter_id}_delete_btn",
                    type="primary",
                    icon=":material/delete:",
                    use_container_width=use_container_width,
                    on_click=delete_confirmation_dialog,
                    args=(filter_id,),
                    help="Delete",
                )

                show_object = toggle_container.pills(
                    "Show Object",
                    options=["Show Filter Object"],
                    key=f"filter_{filter_id}_show_object_toggle_pill",
                    label_visibility="collapsed",
                )

            if show_object:
                st.write(filter_obj)


__all__ = [
    "filter_list",
]
