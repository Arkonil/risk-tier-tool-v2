import numpy as np
import pandas as pd
import streamlit as st

from classes.common import SUB_RISK_TIERS
from classes.iteration_graph import IterationGraph
from classes.session import Session

from views.iterations_widgets.navigation import show_navigation_buttons

color_map = {
    "5B": "hsl(0, 40%, 40%)",
    "5A": "hsl(0, 40%, 40%)",
    "4B": "hsl(30, 40%, 40%)",
    "4A": "hsl(30, 40%, 40%)",
    "3B": "hsl(48, 45%, 40%)",
    "3A": "hsl(48, 45%, 40%)",
    "2B": "hsl(75, 45%, 40%)",
    "2A": "hsl(75, 45%, 40%)",
    "1B": "hsl(120, 40%, 40%)",
    "1A": "hsl(120, 40%, 40%)",
}

@st.dialog("Set Risk Tiers")
def set_risk_tiers(iteration_graph: IterationGraph):
    print("Rerunning Dialog")
    new_labels = st.multiselect(
        label="Risk Tiers",
        options=SUB_RISK_TIERS,
        default=iteration_graph.current_iteration_labels,
        on_change=st.rerun,
    )
    new_labels = list(sorted(new_labels))

    submitted = st.button("Submit")
    if submitted:
        iteration_graph.set_labels(new_labels)
        st.rerun()

def show_edited_range(show_all: bool):
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph
    data = session.data

    iteration = iteration_graph.current_iteration
    labels = iteration_graph.current_iteration_labels

    groups = iteration.groups
    groups = pd.DataFrame({'groups' : groups})

    if iteration_graph.current_iteration_type == "categorical":
        with st.expander("Edit Groups"):
            columns = st.columns(min(5, len(groups)))

            all_categories = set(iteration_graph.current_iteration.variable.cat.categories)
            assigned_categories = set(groups['groups'].explode())
            unassigned_categories = all_categories - assigned_categories

            for row in groups.itertuples():
                group_index = row.Index
                group = set(row.groups)

                with columns[group_index % len(columns)]:
                    new_group = set(st.multiselect(
                        label=labels[group_index],
                        options=sorted(list(group.union(unassigned_categories))),
                        default=sorted(list(group),
                        # disabled=True,
                    )))

                    if group != new_group:
                        iteration.set_group(group_index, new_group)
                        iteration_graph.add_to_calculation_queue()
                        st.rerun()

    st.divider()

    new_risk_tiers, errors, warnings, _ = iteration_graph.get_risk_tiers()

    if not data.all_variable_selected():
        raise ValueError("All the required vaiables are not selected.")

    base_df = pd.DataFrame({
        'risk_tier_value': new_risk_tiers,
        'volume': 1,
        'wo_bal': data.load_column(data.var_dlr_wrt_off),
        'avg_bal': data.load_column(data.var_avg_bal),
        'wo_flag': data.load_column(data.var_unt_wrt_off),
    })

    summ_df = base_df.groupby('risk_tier_value').sum()

    summ_df['wo_bal_perc'] = summ_df['wo_bal'] / summ_df['avg_bal']
    summ_df['wo_flag_perc'] = summ_df['wo_flag'] / summ_df['volume']

    calculated_df = groups.merge(
        summ_df,
        how='left',
        left_index=True,
        right_index=True,
    )

    calculated_df['risk_tier'] = labels

    columns = ['risk_tier']

    if iteration_graph.current_iteration_type == "numerical":
        calculated_df['lower_bound'] = calculated_df['groups'].map(lambda bounds: bounds[0])
        calculated_df['upper_bound'] = calculated_df['groups'].map(lambda bounds: bounds[1])

        columns += ['lower_bound', 'upper_bound']
    else:
        columns += ['groups']

    columns += ['volume', 'wo_bal', 'wo_bal_perc', 'wo_flag', 'wo_flag_perc', 'avg_bal']

    calculated_df = calculated_df[columns]

    int_cols = ['volume', 'wo_flag']
    dec_cols = ['wo_bal', 'avg_bal']
    perc_cols = ['wo_bal_perc', 'wo_flag_perc']

    column_config = {
        'risk_tier': st.column_config.TextColumn(label="Risk Tier", disabled=True),
        'groups': st.column_config.ListColumn(label="Categories", width="large"),
        'lower_bound': st.column_config.NumberColumn(label="Lower Bound", disabled=False),
        'upper_bound': st.column_config.NumberColumn(label="Upper Bound", disabled=False),
        'volume': st.column_config.NumberColumn(label='Volume', disabled=True),
        'wo_bal': st.column_config.NumberColumn(label='Total WO Balance', disabled=True),
        'wo_bal_perc': st.column_config.NumberColumn(label="$ WO %", disabled=True),
        'wo_flag': st.column_config.NumberColumn(label='WO count', disabled=True),
        'wo_flag_perc': st.column_config.NumberColumn(label="# WO %", disabled=True),
        'avg_bal': st.column_config.NumberColumn(label='Total Average Balance', disabled=True),
    }

    if not show_all:
        calculated_df.drop(columns=['wo_bal', 'wo_flag', 'avg_bal'], inplace=True)
        del column_config['wo_bal']
        del column_config['wo_flag']
        del column_config['avg_bal']

        int_cols.remove('wo_flag')
        dec_cols.clear()

    calculated_df = calculated_df.style \
        .map(lambda v: f'background-color: {color_map[v]};', subset=['risk_tier']) \
        .format(precision=0, thousands=',', subset=int_cols) \
        .format(precision=2, thousands=',', subset=dec_cols) \
        .format('{:.2f} %', subset=perc_cols)

    edited_df = st.data_editor(calculated_df, hide_index=True, column_config=column_config, use_container_width=True)

    if iteration_graph.current_iteration_type == "numerical":

        edited_groups = edited_df[['risk_tier', 'lower_bound', 'upper_bound']]

        needs_rerun = False
        for index in edited_groups.index:
            prev_bounds = np.array(groups.loc[index, 'groups']).astype(float)
            curent_bounds = np.array(edited_groups.loc[index, ['lower_bound', 'upper_bound']]).astype(float)

            if not np.array_equal(prev_bounds, curent_bounds, equal_nan=True):
                curr_lb = edited_groups.loc[index, 'lower_bound']
                curr_ub = edited_groups.loc[index, 'upper_bound']

                iteration.set_group(index, curr_lb, curr_ub)
                iteration_graph.add_to_calculation_queue()
                needs_rerun = True

        if needs_rerun:
            print(f"needs rerun: {needs_rerun}")
            st.rerun()

    if errors:
        message = "Errors: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", errors))

        st.error(message, icon=":material/error:")

    if warnings:
        message = "Warnings: \n\n" + "\n\n".join(map(lambda msg: f"- {msg}", warnings))

        st.warning(message, icon=":material/warning:")

        # warning_message = "Warning: \n\n"

        # for group_index, messages in warnings.items():
        #     for msg in messages:
        #         warning_message += f"- Group {group_index}: {msg}\n"

        # st.warning(message, icon=":material/warning:")

def show_single_var_iteration_widgets():
    session: Session = st.session_state['session']
    iteration_graph = session.iteration_graph
    iteration = iteration_graph.iterations[iteration_graph.current_node_id]

    show_navigation_buttons()

    with st.sidebar:
        show_all = st.checkbox("Show all metrics")

        if st.button("Set Risk Tiers", use_container_width=True):
            set_risk_tiers(iteration_graph)

    st.title(f"Iteration #{iteration.id}")
    st.write(f"#### Variable: `{iteration.variable.name}`")

    show_edited_range(show_all=show_all)
