import streamlit as st

from classes.session import Session
from views.metric_widgets.no_metric_placeholder import no_metric_placeholder_widget


def sidebar_widgets():
    session: Session = st.session_state["session"]
    mc = session.metric_container

    if st.button(
        "Create Metric",
        use_container_width=True,
        type="primary",
        icon=":material/add:",
    ):
        mc.set_mode("edit")
        st.rerun()


@st.dialog("Confirm Deletion")
def delete_confirmation_dialog(metric_name: str):
    session: Session = st.session_state["session"]
    mc = session.metric_container

    metric_obj = mc.metrics[metric_name]

    st.write(f"Delete Metric `{metric_obj.name}` ?")

    col1, col2 = st.columns(2)

    with col1:
        if st.button("Delete", type="primary", use_container_width=True):
            mc.remove_metric(metric_name)
            st.rerun()
    with col2:
        if st.button("Cancel", type="secondary", use_container_width=True):
            st.rerun()


def metric_list():
    session: Session = st.session_state["session"]
    mc = session.metric_container

    st.title("Metrics")

    if not mc.metrics:
        no_metric_placeholder_widget()
        return

    with st.sidebar:
        sidebar_widgets()

    for metric_name, metric_obj in mc.metrics.items():
        with st.container(key=f"metric_{metric_name}_container", border=True):
            col1, col2 = st.columns([6, 1], vertical_alignment="center", gap="medium")
            with col1:
                st.markdown(f"### {metric_obj.name}")
                st.code(metric_obj.query, language="python")

            with col2:
                _, toggle_container, _ = st.columns([1, 9, 1])
                col21, col22, col23 = st.columns(3)

                use_container_width = True

                col21.button(
                    label="",
                    key=f"metric_{metric_name}_edit_btn",
                    type="primary",
                    icon=":material/edit:",
                    use_container_width=use_container_width,
                    on_click=mc.set_mode,
                    args=("edit", metric_name),
                    help="Edit",
                )

                col22.button(
                    label="",
                    key=f"metric_{metric_name}_create_dupicate_btn",
                    type="primary",
                    icon=":material/content_copy:",
                    use_container_width=use_container_width,
                    on_click=mc.duplicate_metric,
                    args=(metric_name,),
                    help="Create Duplicate",
                )

                col23.button(
                    label="",
                    key=f"metric_{metric_name}_delete_btn",
                    type="primary",
                    icon=":material/delete:",
                    use_container_width=use_container_width,
                    on_click=delete_confirmation_dialog,
                    args=(metric_name,),
                    help="Delete",
                )

                show_object = toggle_container.pills(
                    "Show Object",
                    options=["Show Metric Object"],
                    key=f"metric_{metric_name}_show_object_toggle_pill",
                    label_visibility="collapsed",
                )

            if show_object:
                st.write(metric_obj)


__all__ = [
    "metric_list",
]
