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
    fc = session.filter_container

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

    # Filter Selector
    current_filters = iteration_graph.get_metadata(iteration_id, "filters")

    filter_ids = set(
        st.multiselect(
            label="Filter",
            options=list(fc.filters.keys()),
            default=current_filters,
            format_func=lambda filter_id: fc.filters[filter_id].pretty_name,
            label_visibility="collapsed",
            key=f"filter_selector_{iteration_id}",
            help="Select filters to apply to the iteration",
            placeholder="Select Filters",
        )
    )

    if filter_ids != current_filters:
        iteration_graph.set_metadata(iteration_id, "filters", filter_ids)
        st.rerun()

    # Scalar Toggle
    current_scalars_enabled = iteration_graph.get_metadata(
        iteration_id, "scalars_enabled"
    )

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=current_scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != current_scalars_enabled:
        iteration_graph.set_metadata(iteration_id, "scalars_enabled", scalars_enabled)
        st.rerun()


def single_var_iteration_widgets():
    session: Session = st.session_state["session"]
    iteration_graph = session.iteration_graph

    iteration = iteration_graph.current_iteration

    metrics = iteration_graph.get_metadata(iteration.id, "metrics")
    scalars_enabled = iteration_graph.get_metadata(iteration.id, "scalars_enabled")
    filter_ids = iteration_graph.get_metadata(iteration.id, "filters")

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
        scalars_enabled=scalars_enabled,
        metrics=showing_metrics,
        default=True,
        filter_ids=filter_ids,
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
        scalars_enabled=scalars_enabled,
        metrics=showing_metrics,
        default=False,
        filter_ids=filter_ids,
        key=1,
    )


__all__ = ["single_var_iteration_widgets"]
