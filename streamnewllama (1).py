# -*- coding: utf-8 -*-
"""Streamlitllama.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/1n-7TWKKGqOrJhaJyKS2_bk1x5VUCPQOz
"""

import streamlit as st
from streamlit_folium import folium_static
import pandas as pd
import folium
import plotly.express as px
from datetime import datetime
from openai import OpenAI
import base64
import requests


# Define API details
model = "meta-llama/Llama-3.3-70B-Instruct"
openai_api_key = st.secrets.get("OPENAI_API") or os.getenv("OPENAI_API")
openai_api_base = st.secrets.get("OPENAI_API_BASE") or os.getenv("OPENAI_API_BASE", "https://llm.dsrs.illinois.edu/v1")

# Check if API key is set
if not openai_api_key:
    st.error("OpenAI API key is not set. Please check Streamlit secrets or .env file.")
    st.stop()


client = OpenAI(
    api_key=openai_api_key,
    base_url=openai_api_base,
)

GEOJSON_URLS = {
    "US": "https://raw.githubusercontent.com/PublicaMundi/MappingAPI/master/data/geojson/us-states.json",
    "WORLD": "https://raw.githubusercontent.com/johan/world.geo.json/master/countries.geo.json",
    "CONTINENTS": "https://raw.githubusercontent.com/PhantomInsights/world-geojson/main/continents.json"
}

@st.cache

def fetch_geojson(url):
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"Error fetching GeoJSON: {e}")
        return None

def generate_data_from_ai(prompt):
    try:
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "You are a helpful AI assistant, please be friendly and brief."},
                {"role": "user", "content": f"'{prompt}'"},
                {"role": "assistant", "content": ""}
            ],
            max_tokens=4000,
            stream=False,
        )
        return completion.choices[0].message.content.strip()
    except Exception as e:
        st.error(f"Error querying AI: {e}")
        return None

def parse_ai_data(ai_data):
    try:
        rows = [
            row.strip("| ").split("|")
            for row in ai_data.split("\n")
            if "|" in row and "---" not in row
        ]
        columns = [col.strip() for col in rows[0]]
        data = [[cell.strip() for cell in row] for row in rows[1:]]
        return pd.DataFrame(data, columns=columns)
    except Exception as e:
        st.error(f"Error processing AI-generated data: {e}")
        return None

def main():
    st.title("AI-Generated Data Visualization App")
    st.sidebar.title("Input Parameters")
    business_scenario = st.sidebar.text_input("Enter the business scenario (e.g., Sales Forecasting, Customer Segmentation):")
    data_type = st.sidebar.selectbox("Choose the type of data to generate:", ["Time Series", "Geomap", "Other (Pie, Bar, Scatter)", "Data Only"])
    num_rows = st.sidebar.number_input("Enter the number of entries to generate:", min_value=1, step=1)

    # Chart Customization Options
    st.sidebar.title("Chart Customization")
    chart_title = st.sidebar.text_input("Chart Title:", "My Chart")
    x_axis_label = st.sidebar.text_input("X-Axis Label:", "Category")
    y_axis_label = st.sidebar.text_input("Y-Axis Label:", "Value")
    color_scheme = st.sidebar.color_picker("Pick a Color Scheme:", "#4CAF50")

    granularity = None
    visualization_type = None

    if data_type == "Geomap":
        granularity = st.selectbox("Choose granularity for Geomap:", ["US States", "Countries", "Continents"])
    elif data_type == "Time Series":
        granularity = st.selectbox("Enter granularity:", ["Day", "Month", "Year"])
    elif data_type == "Other (Pie, Bar, Scatter)":
        visualization_type = st.selectbox("Select Visualization Type:", ["Pie", "Bar", "Scatter"])

    specifications = st.text_area("Enter specifications for AI data generation:")

    if st.button("Generate Data"):
        if data_type == "Geomap":
            category_level = "states" if granularity == "US States" else "countries" if granularity == "Countries" else "continents"
            prompt = (
                f"Generate {num_rows} rows of geomap data for the following scenario: {business_scenario}. "
                f"Specifications: {specifications}. "
                f"Output the data with the fields: Category, Subcategory, and Value (in relevant units). "
                f"Ensure that the 'Category' field contains {category_level}, and 'Value' contains numeric or quantifiable values."
            )
        elif data_type == "Time Series":
            prompt = (
                f"Generate {num_rows} rows of time series data for the following scenario: {business_scenario}. "
                f"Specifications: {specifications}. "
                f"Output the data with the fields: Category, Subcategory, and Value (in relevant units). "
                f"Ensure that the 'Category' field reflects the {granularity} granularity and 'Value' contains numeric or quantifiable values."
            )
        else:
            prompt = (
                f"Generate {num_rows} rows of data for the following scenario: {business_scenario}. "
                f"Specifications: {specifications}. "
                f"Output the data with the fields: Category, Subcategory, and Value (in relevant units). "
                f"Ensure that the 'Value' field contains numeric or quantifiable values."
            )

        ai_data = generate_data_from_ai(prompt)

        if ai_data:
            df = parse_ai_data(ai_data)

            if df is not None:
                if set(['Category', 'Value']).issubset(df.columns):
                    try:
                        df['Value'] = df['Value'].str.replace(',', '')
                        df['Value'] = df['Value'].str.extract(r'(\d+(\.\d+)?)')[0]
                        df['Value'] = pd.to_numeric(df['Value'], errors='coerce')
                    except Exception as e:
                        st.error(f"Error cleaning 'Value' column: {e}")

                    st.write("Generated Data:")
                    st.dataframe(df)

                    selected_category = st.selectbox("Filter by Category", df["Category"].unique())
                    filtered_data = df[df["Category"] == selected_category]
                    st.dataframe(filtered_data)


                    if data_type == "Time Series":
                        fig = px.line(df, x="Category", y="Value", title="Time Series Data", markers=True)
                        st.plotly_chart(fig)

                    elif data_type == "Geomap":
                        geojson_data = fetch_geojson(GEOJSON_URLS.get("US" if granularity == "US States" else "WORLD" if granularity == "Countries" else "CONTINENTS"))
                        if geojson_data:
                            m = folium.Map(location=[20, 0], zoom_start=2)
                            folium.Choropleth(
                                geo_data=geojson_data,
                                name="choropleth",
                                data=df,
                                columns=["Category", "Value"],
                                key_on="feature.properties.name",
                                fill_color="YlGnBu",
                                fill_opacity=0.7,
                                line_opacity=0.2,
                                legend_name="Value",
                            ).add_to(m)
                            folium_static(m)

                    elif data_type == "Other (Pie, Bar, Scatter)":
                        if visualization_type == "Pie":
                            fig = px.pie(df, names="Category", values="Value", title= chart_title)
                            fig.update_traces(hoverinfo="label+percent+name")  # Add detailed hover info
                        elif visualization_type == "Bar":
                            fig = px.bar(df, x="Category", y="Value", color="Subcategory", title= chart_title, labels={"Category": x_axis_label, "Value": y_axis_label})
                            fig.update_traces(hoverinfo="x+y+text")  # Customize hover info for bar charts
                        elif visualization_type == "Scatter":
                            fig = px.scatter(df, x="Category", y="Value", color="Subcategory", title= chart_title)
                            fig.update_traces(hoverinfo="x+y+name")  # Add hover info for line chart
                        st.plotly_chart(fig)
                        fig.update_traces(hoverinfo="label+percent+name")
                    # Apply Custom Color Scheme
                        fig.update_traces(marker_color=color_scheme)

                    csv = df.to_csv(index=False)
                    b64 = base64.b64encode(csv.encode()).decode()
                    href = f'<a href="data:file/csv;base64,{b64}" download="generated_data.csv">Download CSV</a>'
                    st.markdown(href, unsafe_allow_html=True)
                else:
                    st.error("AI-generated data does not contain the required fields: Category, Value")

if __name__ == "__main__":
    main()
