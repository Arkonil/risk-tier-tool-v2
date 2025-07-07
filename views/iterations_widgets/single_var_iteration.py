import streamlit as st

from classes.constants import (
    MetricTableColumn,
    VariableType,
)
from classes.session import Session
from views.iterations_widgets.common import (
    category_editor_widget,
    get_risk_tier_details,
    editable_range_widget,
)
from views.iterations_widgets.dialogs import metric_selector_dialog_widget
from views.iterations_widgets.navigation import navigation_widgets
from views.components import variable_selector_dialog_widget


def sidebar_widgets(iteration_id: str):
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration_metadata = iteration_graph.iteration_metadata[iteration_id]

    st.button(
        label="Set Variables",
        use_container_width=True,
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=variable_selector_dialog_widget,
    )

    st.button(
        label="Set Metrics",
        use_container_width=True,
        icon=":material/functions:",
        help="Set metrics to display in the table",
        on_click=metric_selector_dialog_widget,
        args=(iteration_id,),
    )

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=iteration_metadata["scalars_enabled"],
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != iteration_metadata["scalars_enabled"]:
        iteration_metadata["scalars_enabled"] = scalars_enabled
        st.rerun()


def single_var_iteration_widgets():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.current_iteration
    iteration_metadata = iteration_graph.iteration_metadata[iteration.id]

    metrics = iteration_metadata["metrics"]
    showing_metrics = (
        metrics.sort_values(MetricTableColumn.ORDER)
        .loc[metrics[MetricTableColumn.SHOWING], MetricTableColumn.METRIC]
        .to_list()
    )

    # Sidebar
    with st.sidebar:
        sidebar_widgets(iteration_id=iteration.id)

    # Main Page
    ## Navigation
    navigation_widgets()

    st.title(f"Iteration #{iteration.id}")
    st.write(f"##### Variable: `{iteration.variable.name}`")

    ## Risk Tier Details Check
    _, message = get_risk_tier_details(iteration.id, recheck=True)

    if message:
        st.error(message, icon=":material/error:")

    ## Default View

    st.markdown("##### Default Range")
    editable_range_widget(
        iteration_id=iteration.id,
        editable=True,
        scalars_enabled=iteration_metadata["scalars_enabled"],
        metrics=showing_metrics,
        default=True,
        key=0,
    )

    ## Category Editor
    if iteration.var_type == VariableType.CATEGORICAL:
        category_editor_widget(iteration.id)

    ## Ranges
    st.markdown("##### Editable Ranges")
    editable_range_widget(
        iteration_id=iteration.id,
        editable=True,
        scalars_enabled=iteration_metadata["scalars_enabled"],
        metrics=showing_metrics,
        default=False,
        key=1,
    )


__all__ = ["single_var_iteration_widgets"]
