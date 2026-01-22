import typing as t

import streamlit as st
import streamlit_antd_components as sac

from risc_tool.data.models.enums import (
    IterationType,
    RangeColumn,
)
from risc_tool.data.models.types import IterationID
from risc_tool.data.session import Session
from risc_tool.pages.components.metric_selector import metric_selector_button
from risc_tool.pages.components.variable_selector import variable_selector_dialog


@st.dialog("Set Groups")
def set_groups_dialog_widget(iteration_id: IterationID):
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    groups = iterations_vm.get_all_groups(iteration_id)

    if RangeColumn.SELECTED not in groups.columns:
        st.exception(ValueError("RangeColumn.SELECTED not in groups.columns"))
        return

    column_config = {
        RangeColumn.CATEGORIES.value: st.column_config.ListColumn(
            label=RangeColumn.CATEGORIES, width="large"
        ),
        RangeColumn.LOWER_BOUND.value: st.column_config.NumberColumn(
            label=RangeColumn.LOWER_BOUND, disabled=True, format="compact"
        ),
        RangeColumn.UPPER_BOUND.value: st.column_config.NumberColumn(
            label=RangeColumn.UPPER_BOUND, disabled=True, format="compact"
        ),
        RangeColumn.SELECTED.value: st.column_config.CheckboxColumn(
            label=RangeColumn.SELECTED, disabled=False
        ),
    }

    edited_groups = st.data_editor(
        groups,
        column_config=column_config,
        width="stretch",
    )

    _, col = st.columns(2)

    with col:
        if st.button("Submit", type="primary", width="stretch"):
            iterations_vm.select_groups(
                iteration_id,
                edited_groups[edited_groups[RangeColumn.SELECTED]].index.to_list(),
            )
            st.rerun()


def iteration_sidebar_components(iteration_id: IterationID):
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    iteration = iterations_vm.iterations.get(iteration_id, None)

    if iteration is None:
        return

    st.button(
        label="Set Variables",
        width="stretch",
        icon=":material/data_table:",
        help="Select variables for calculations",
        type="primary",
        on_click=variable_selector_dialog,
    )

    metric_selector_button(
        current_metrics=iterations_vm.get_iteration_metadata(iteration_id).metric_ids,
        set_metrics=lambda metric_ids: iterations_vm.set_metadata(
            iteration_id=iteration_id,
            metric_ids=metric_ids,
        ),
    )

    if iteration.iter_type == IterationType.DOUBLE:
        col1, col2 = st.columns([3, 1])

        col1.button(
            label="Edit Groups",
            use_container_width=True,
            icon=":material/edit:",
            on_click=lambda: set_groups_dialog_widget(iteration_id),
        )

        col2.button(
            label="",
            use_container_width=True,
            icon=":material/add:",
            key="Add Group",
            on_click=lambda: iterations_vm.add_new_group(iteration_id),
        )

    # Filter Selection
    current_filter_ids = iterations_vm.get_iteration_metadata(
        iteration_id
    ).current_filter_ids
    all_filters = iterations_vm.get_filters()

    selected_filter_ids = st.multiselect(
        label="Filter",
        options=iterations_vm.get_filters().keys(),
        default=current_filter_ids,
        format_func=lambda filter_id: all_filters[filter_id].pretty_name,
        label_visibility="collapsed",
        key=f"filter_selector_{iteration_id}",
        help="Select filters to apply to the iteration",
        placeholder="Select Filters",
    )

    if set(selected_filter_ids) != set(current_filter_ids):
        iterations_vm.set_metadata(
            iteration_id=iteration_id,
            filter_ids=selected_filter_ids,
        )
        st.rerun()

    # Split View Toggle
    if iteration.iter_type == IterationType.DOUBLE:
        current_split_view_enabled = iterations_vm.get_iteration_metadata(
            iteration_id
        ).split_view_enabled

        selected_idx = sac.segmented(
            [
                sac.SegmentedItem("list", "list"),
                sac.SegmentedItem("grid", "grid"),
            ],
            use_container_width=True,
            size="sm",
            index=1 if current_split_view_enabled else 0,
            key=f"split-view-{iteration_id}",
            return_index=True,
        )

        split_view_enabled = selected_idx == 1

        if split_view_enabled != current_split_view_enabled:
            iterations_vm.set_metadata(
                iteration_id=iteration_id,
                split_view_enabled=split_view_enabled,
            )
            st.rerun()

    # Scalar Toggle
    current_scalars_enabled = iterations_vm.get_iteration_metadata(
        iteration_id
    ).scalars_enabled

    scalars_enabled = st.checkbox(
        label="Enable Scalars",
        value=current_scalars_enabled,
        help="Use Scalars for Annualized Write Off Rates",
    )

    if scalars_enabled != current_scalars_enabled:
        iterations_vm.set_metadata(
            iteration_id=iteration_id,
            scalars_enabled=scalars_enabled,
        )
        st.rerun()

    # Editable Toggle
    if iteration.iter_type == IterationType.DOUBLE:
        current_editable = iterations_vm.get_iteration_metadata(iteration_id).editable

        editable = st.checkbox(
            label="Editable",
            value=current_editable,
            help="Editable",
        )

        if editable != current_editable:
            iterations_vm.set_metadata(iteration_id, editable=editable)
            st.rerun()

    # Show Previous Iteration Details
    if iteration.iter_type == IterationType.DOUBLE:
        current_iteration_depth = iterations_vm.iteration_graph.iteration_depth(
            iteration_id
        )
        if current_iteration_depth == 2:
            current_show_prev_iter_details: bool = iterations_vm.get_iteration_metadata(
                iteration_id
            ).show_prev_iter_details

            show_prev_iter_details = st.checkbox(
                label="Show Previous Iteration Details",
                value=current_show_prev_iter_details,
                help="Show Previous Iteration Details",
            )

            if show_prev_iter_details != current_show_prev_iter_details:
                iterations_vm.set_metadata(
                    iteration_id,
                    show_prev_iter_details=show_prev_iter_details,
                )
                st.rerun()


def check_current_rs_details():
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    iteration = iterations_vm.current_iteration

    if iteration is None:
        return

    is_same = iterations_vm.is_rs_details_same(iteration.uid)

    if is_same == "equal":
        return

    message = "Risk Segment Details have been changed after creating the iteration."

    if is_same == "unequal":
        message += " All calculations will be done with the original details."

        with st.expander(
            label="Error: Risk Segment Details not updated",
            expanded=False,
            icon=":material/error:",
        ):
            st.error(body=message, icon=":material/error:")

        return

    if is_same == "updatable":
        message += " Update?"

        with st.container(horizontal=True):
            st.warning(message, icon=":material/warning:")

            st.button(
                label="Update",
                width="content",
                icon=":material/refresh:",
                on_click=lambda: iterations_vm.update_rs_details(iteration.uid),
            )


def editable_grid_widget(
    iteration_id: IterationID,
    default: bool,
    key: str,
):
    session: Session = st.session_state["session"]
    iterations_vm = session.iterations_view_model

    editable = (
        iterations_vm.get_iteration_metadata(iteration_id).editable and not default
    )
    grid_components = iterations_vm.get_editable_grid(iteration_id, default, editable)
    show_prev_iter_details = grid_components["show_prev_iter_details"]

    column_config = {}

    if grid_components["lower_bound_pos"] is not None:
        column_config[grid_components["lower_bound_pos"]] = (
            st.column_config.NumberColumn(
                width=100,
                format="compact",
                disabled=not editable or default,
                pinned=True,
            )
        )

    if grid_components["upper_bound_pos"] is not None:
        column_config[grid_components["upper_bound_pos"]] = (
            st.column_config.NumberColumn(
                width=100,
                format="compact",
                disabled=not editable or default,
                pinned=True,
            )
        )

    if grid_components["categories_pos"] is not None:
        column_config[grid_components["categories_pos"]] = (
            st.column_config.MultiselectColumn(
                width=200,
                disabled=not editable or default,
                pinned=True,
                options=iterations_vm.get_categorical_iteration_options(iteration_id),
                color="auto",
            )
        )

    for col_pos in grid_components["risk_segment_grid_col_pos"]:
        column_config[col_pos] = st.column_config.SelectboxColumn(
            disabled=not editable or default,
            options=grid_components["grid_options"],
            required=True,
        )

    key = f"edited_grid-{key}-{iteration_id}"

    def grid_edit_handler():
        edited_rows: dict[int, dict[str, t.Any]] = st.session_state[key]["edited_rows"]

        edited_final_df = grid_components["styler"].data.copy()  # type: ignore

        for row_index, row_change in edited_rows.items():
            for col_index, change in row_change.items():
                edited_final_df.at[row_index, col_index] = change

        iterations_vm.editable_grid_edit_handler(iteration_id, default, edited_final_df)

    with st.container(height=30, border=False):
        st.markdown("##### Risk Segment Grid")

    if (
        editable
        and iterations_vm.get_iteration_metadata(iteration_id).show_prev_iter_details
        and iterations_vm.get_iteration_metadata(iteration_id).split_view_enabled
        and iterations_vm.iteration_graph.iteration_depth(iteration_id) == 2
    ):
        st.space(size=20)

    if show_prev_iter_details or not editable:
        st.dataframe(
            data=grid_components["styler"],
            width="stretch",
            hide_index=True,
            column_config=column_config,
            key=key,
            placeholder="-",
        )
    else:
        if (
            editable
            and not iterations_vm.get_iteration_metadata(
                iteration_id
            ).show_prev_iter_details
        ) or iterations_vm.iteration_graph.iteration_depth(iteration_id) != 2:
            height = "auto"
        else:
            height = int(min((len(grid_components["styler"].data) + 1) * 35.5, 364))  # type: ignore

        st.data_editor(
            data=grid_components["styler"],
            width="stretch",
            hide_index=True,
            column_config=column_config,
            key=key,
            height=height,
            placeholder="-",
            on_change=grid_edit_handler,
        )


__all__ = [
    "iteration_sidebar_components",
    "check_current_rs_details",
    "editable_grid_widget",
]
