import typing as t

import streamlit as st
import streamlit_antd_components as sac

from risc_tool.data.session import Session


def data_viewer():
    session: Session = st.session_state["session"]
    data_importer_view_model = session.data_importer_view_model

    if not data_importer_view_model.data_source_views:
        return

    current_ds_id = data_importer_view_model.current_ds_id

    if current_ds_id is None:
        return

    data_source_views = data_importer_view_model.data_source_views
    ds_ids = [ds_id for ds_id in data_source_views]

    tabs: list[sac.TabsItem | str | dict] = [
        sac.TabsItem(dsv.data_source.label) for dsv in data_source_views.values()
    ]

    selected_tab_index = sac.tabs(
        tabs,
        index=ds_ids.index(current_ds_id),
        return_index=True,
    )

    selected_tab_index = t.cast(int, selected_tab_index)
    selected_ds_id = ds_ids[selected_tab_index]

    if selected_ds_id != current_ds_id:
        data_importer_view_model.current_ds_id = selected_ds_id
        st.rerun()

    sample_df = data_importer_view_model.data_source_views[
        selected_ds_id
    ].data_source._sample_df

    if sample_df is None:
        return

    st.dataframe(sample_df)


__all__ = ["data_viewer"]
