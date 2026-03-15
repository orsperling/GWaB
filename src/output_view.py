import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


def render_outputs(df_irrigation, ndvi, latest_date, rain, unit_label, conversion_factor, irrigation_months, winter_irrigation):
    k_crop = float(df_irrigation['K_crop'].iloc[0])
    summer_irrigation = float(df_irrigation['summer_irrigation'].iloc[0])
    total_irrigation = float(winter_irrigation) + summer_irrigation

    st.markdown(f"""
    <div style='text-align: center; font-size: 30px;'>
        NDVI: {ndvi:.2f} | Transpiration Coefficient: {k_crop:.2f} | Water Allocation: {total_irrigation:.0f} {unit_label}
    </div>
    """, unsafe_allow_html=True)

    st.subheader('Monthly Works:')

    table_col, plot_col = st.columns(2)

    with plot_col:
        fig, ax = plt.subplots()

        start_month, end_month = irrigation_months
        plot_df = df_irrigation[df_irrigation['month'].between(start_month, end_month)].copy()
        plot_df['cumsum_irrigation'] = plot_df['irrigation'].cumsum()

        ax.bar(
            plot_df.loc[plot_df['alert'] == 'safe', 'month'],
            plot_df.loc[plot_df['alert'] == 'safe', 'cumsum_irrigation'],
            alpha=1,
            label="Irrigation",
        )

        if (plot_df['soil_budget'] < 0).any():
            ax.bar(
                plot_df.loc[plot_df['alert'] == 'drought', 'month'],
                plot_df.loc[plot_df['alert'] == 'drought', 'cumsum_irrigation'],
                alpha=1,
                label="Deficit Irrigation",
                color='#FF4B4B',
            )

        ax.fill_between(
            plot_df['month'],
            0,
            plot_df['soil_budget'],
            color='#74ac72',
            alpha=0.4,
            label="Water Budget",
        )

        ax.set_xlabel("Month")
        ax.set_ylabel(f"Water ({unit_label})")
        ax.legend()
        st.pyplot(fig)

    with table_col:
        filtered_df = df_irrigation[df_irrigation['month'].between(irrigation_months[0], irrigation_months[1])].copy()
        filtered_df['month'] = pd.to_datetime(filtered_df['month'], format='%m').dt.month_name()
        st.dataframe(
            filtered_df[['month', 'ET0', 'ETcrop', 'irrigation', 'soil_budget']]
            .rename(columns={
                'month': '',
                'ET0': f'ET₀ ({unit_label})',
                'ETcrop': f'ETcrop ({unit_label})',
                'irrigation': f'Irrigation ({unit_label})',
                'soil_budget': f'Soil Budget ({unit_label})',
            }).round(1),
            hide_index=True,
            use_container_width=True,
        )
