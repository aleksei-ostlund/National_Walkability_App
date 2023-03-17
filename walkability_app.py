# walkability_app.py

import pandas as pd
import streamlit as st
import plotly.express as px
from urllib.request import urlopen
import json

walkability_df = pd.read_csv('walkability_2021_clean.csv', dtype={'SCFP': str})

nationwide_mean= walkability_df['NatWalkInd'].mean()

#group by state and get mean walk score
by_state_grouped= walkability_df.groupby(['STATE'], as_index=False).agg(
    {'NatWalkInd':'mean',
     'population':'sum'}).sort_values('NatWalkInd', ascending=False)
states_10= by_state_grouped.head(10).sort_values('STATE')
states_10= states_10.rename(columns={'NatWalkInd':'Avg NatWalkInd'})

# ------------------------------------------------------------------
#streamlit app
st.set_page_config(layout="wide")

col1, col2 = st.columns(2, gap="large")
hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """

st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.sidebar.title("How Walkable is the United States?")

natwalkind_cats= pd.DataFrame(
    {'Classification': ['Least walkable', 
                        'Below average walkable',
                        'Above average walkable', 
                        'Most walkable'], 
    'National Walkability Index' : ['1 - 5.75', 
                                   '5.76 - 10.5', 
                                   '10.51 - 15.25', 
                                   '15.26 - 20']})
natwalkind_cats.set_index('Classification', inplace=True)


st.sidebar.header("The National Walkability Index")
st.sidebar.write("""The EPA developed the
National Walkability Index, a measure of
the relative walkability of areas in the United States.""") 
st.sidebar.write("""The index is derived from the built environment and how likely people are to use walk to their chosen destination.""")
         
st.sidebar.write("""
The variables that determine the index score are: intersection density, 
proximity to transit stops, diversity of land use, employment mix, and employment/household mix.""")

st.sidebar.write("The EPA has designated four classifications based on the national walkability index score.")
st.sidebar.write(natwalkind_cats)


#GRAPH % of population above 15.25
state_populations= walkability_df.groupby(['STATE'], as_index=False)
state_populations= state_populations.agg({'population':'sum'})
state_populations.rename(columns={'TotPop': 'total_population'}, inplace=True)

walkable_population= walkability_df[walkability_df['NatWalkInd'] >= 15.25].groupby(['STATE'], as_index=False)
walkable_population= walkable_population.agg({'population':'sum'})
walkable_population.rename(columns={'population':'walkable_population'}, inplace=True)

pct_walkable= pd.merge(left=state_populations, right=walkable_population, on='STATE', how='left')
pct_walkable.fillna(0, inplace=True)
pct_walkable["walkable_population_pct"]= round((pct_walkable.iloc[:,-1] / pct_walkable.iloc[:,1])*100, 2)

pct_walkable['walkable_population'] = pct_walkable['walkable_population'].astype('int64')
pct_walkable= pct_walkable.sort_values('STATE', ascending=False)

pct_walkable_graph= px.bar(pct_walkable, x='walkable_population_pct', y='STATE', height=1100, width=600,
                           title='Percent of population classified as living in "most walkable" blocks')
pct_walkable_graph.update_layout(xaxis_title="Percent of population with walk index above 15.25")
pct_walkable_graph.update_traces(marker={"color":'#75b56d'})
pct_walkable_graph.update_layout(yaxis_title='State')
nationwide_mean_walkable= pct_walkable['walkable_population_pct'].mean()
pct_walkable_graph.add_vline(x=nationwide_mean_walkable, line_width=3, line_dash="dash", line_color="orange",
                   annotation_text='state-level average')

col1.write(pct_walkable_graph)

#write map
with urlopen('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json') as response:
    fips_counties = json.load(response)

map_fig = px.choropleth(walkability_df, 
                        geojson=fips_counties, 
                        locations='SCFP', 
                        color='NatWalkInd',
                        color_continuous_scale="algae",
                        range_color=(0, 20),
                        scope="usa",
                        labels={'NatWalkInd':'National Walk Index Score'}
                        )
map_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0})
map_fig.update_layout(geo=dict(bgcolor= 'rgba(0,0,0,0)'))
col2.write(map_fig)

#write graph that shows the most walkable counties for selected states
def graph_most_walkable_counties(state):
    by_county_grouped= walkability_df.groupby(['STATE','COUNTY'], as_index=False).agg(
    {'NatWalkInd':'mean',
     'population':'sum'})
    counties= by_county_grouped[by_county_grouped['STATE'] == state].sort_values('NatWalkInd', ascending=False)
    counties= counties.head(15).sort_values('COUNTY')
    counties.rename(columns={'population':'COUNTY POPULATION'}, inplace=True)
    
    if len(state)>0:
        county_bar= px.bar(counties, x='NatWalkInd', y='COUNTY', orientation='h',
                 title='Counties in {} with the highest average walkability score'.format(str(state).strip("[]")),
                 template='plotly_dark',
                 hover_data=['COUNTY POPULATION', 'STATE'],
                 height=500, width=600)
        county_bar.update_layout(xaxis_range=[0,20],
                        xaxis_title='Average National Walk Index Score',
                        yaxis_title='County')
        county_bar.add_vline(x=nationwide_mean, line_width=3, line_dash="dash", line_color="orange",
                   annotation_text='nationwide average')
        county_bar.update_traces(marker={"color":'#a3e6e3'})

    else:
        county_bar= px.bar(counties, x='NatWalkInd', y='COUNTY', orientation='h',
                 title='No states selected'.format(state),
                 template='plotly_dark',
                 hover_data=['COUNTY POPULATION', 'STATE'],
                 height=500, width=600)
        county_bar.update_layout(xaxis_range=[0,20],
                        xaxis_title='Average National Walk Index Score',
                        yaxis_title='County')
        county_bar.add_vline(x=nationwide_mean, line_width=3, line_dash="dash", line_color="orange",
                   annotation_text='nationwide average')
        
    return county_bar

#select box
states_list= sorted(walkability_df['STATE'].unique())
state_selections = col2.selectbox('Select a state to see its most walkable counties in the graph below',
                                  states_list)

col2.write(graph_most_walkable_counties(state_selections))

#write graph of top states on average
states_10_bar= px.bar(states_10, x='Avg NatWalkInd', y='STATE', orientation='h',
                 title='States with the highest average walkability score',
                 template='plotly_dark',
                 hover_data=['population'],
                 width=600)
states_10_bar.update_layout(xaxis_range=[0,20],
                        xaxis_title='Average National Walk Index Score',
                        yaxis_title='State')
states_10_bar.add_vline(x=nationwide_mean, line_width=3, line_dash="dash", line_color="orange",
                   annotation_text='nationwide average')
states_10_bar.update_traces(marker={"color":'#75b56d'})
col1.write(states_10_bar)

#graph CSA's with best transit proximity
transit= walkability_df.groupby('CSA_Name')
transit= transit.agg({'ranked_transit_proximity':'mean',
                        'population':'sum'}).sort_values('ranked_transit_proximity').sort_values('ranked_transit_proximity',ascending=False)
transit= transit[transit['population'] >= 1000000].head(10)

transit_graph= px.bar(transit, x='CSA_Name', y='ranked_transit_proximity',
                           title='Average transit proximity score by CSA')
col2.write(transit_graph)