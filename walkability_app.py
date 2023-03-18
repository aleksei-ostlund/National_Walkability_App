# walkability_app.py

import pandas as pd
import streamlit as st
st.set_page_config(page_title='National Walkability Index Dashboard', layout='wide')
import plotly.express as px
from urllib.request import urlopen
import json

@st.cache_data
def load_data(csv_file):
    df= pd.read_csv(csv_file, dtype={'SCFP': str})
    return df

walkability_df = load_data('walkability_2021_clean.csv')
nationwide_mean= walkability_df['NatWalkInd'].mean()

# ------------------------------------------------------------------
#streamlit app
hide_streamlit_style = """
        <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        </style>
        """

st.markdown(hide_streamlit_style,unsafe_allow_html=True)

st.sidebar.title("How Walkable is the United States?")

natwalkind_cats= pd.DataFrame(
    {'Classification': ['Least walkable', 
                        'Below avg. walkable',
                        'Above avg. walkable', 
                        'Most walkable'], 
    'NWI score' : ['1-5.75', 
                   '5.76-10.5',
                   '10.51-15.25',
                   '15.26-20']})
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

top_row= st.container()
select_row= st.container()
big_row= st.container()
bottom_row= st.container()

with top_row:
    st.write('**National Walkability Index by county**')
    #write map
    @st.cache_data
    def mk_fips_counties(url):
        with urlopen(url) as response:
            fips = json.load(response)
        return fips

    fips_counties= mk_fips_counties('https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json')

    @st.cache_data
    def mk_map(df):
        map_fig = px.choropleth(df, 
                            geojson=fips_counties, 
                            locations='SCFP', 
                            color='NatWalkInd',
                            color_continuous_scale="algae",
                            range_color=(0, 20),
                            scope="usa",
                            labels={'NatWalkInd':'Average Score'},
                            )
        map_fig.update_layout(margin={"r":0,"t":0,"l":0,"b":0,'autoexpand':True})
        map_fig.update_layout(geo=dict(bgcolor= 'rgba(0,0,0,0)'))
        map_fig.update_layout(autosize=True)
        return map_fig
    st.plotly_chart(mk_map(walkability_df), use_container_width=True)

    

with select_row:
    #write graph that shows the most walkable counties for selected states
        @st.cache_data
        def mk_county_df(df):
            grouped= df.groupby(['STATE','COUNTY'], as_index=False).agg(
            {'NatWalkInd':'mean',
            'population':'sum'})
            return grouped

        grouped= mk_county_df(walkability_df)

        def graph_most_walkable_counties(grouped, state):
            counties= grouped[grouped['STATE'] == state].sort_values('NatWalkInd', ascending=False)
            counties= counties.head(15).sort_values('COUNTY')
            counties.rename(columns={'population':'COUNTY POPULATION'}, inplace=True)
            
            county_bar= px.bar(counties, x='NatWalkInd', y='COUNTY', orientation='h',
                        title='Counties in {} with the highest average walkability score'.format(str(state).strip("[]")),
                        template='plotly_dark',
                        hover_data=['COUNTY POPULATION', 'STATE'],
                        height=550, width=500)
            county_bar.update_layout(xaxis_range=[0,20],
                                xaxis_title='Average National Walk Index Score',
                                yaxis_title='County')
            county_bar.add_vline(x=nationwide_mean, line_width=3, line_dash="dash", line_color="orange",
                        annotation_text='nationwide average')
            county_bar.update_traces(marker={"color":'#a3e6e3'})
                
            return county_bar

        #select box
        @st.cache_data
        def get_states(df):
            states_list= sorted(df['STATE'].unique())
            return states_list

        states_list= get_states(walkability_df)

        state_selections = st.selectbox('Select a state/territory to see its most walkable counties in the graph below',
                                        states_list, index=32 )

        st.plotly_chart(graph_most_walkable_counties(grouped,state_selections), use_container_width=True)

 
with big_row:
    #GRAPH % of population above 15.25
    @st.cache_data
    def mk_wlk(df):
        state_populations= df.groupby(['STATE'], as_index=False)
        state_populations= state_populations.agg({'population':'sum'})
        state_populations.rename(columns={'TotPop': 'total_population'}, inplace=True)

        walkable_population= df[df['NatWalkInd'] >= 15.25].groupby(['STATE'], as_index=False)
        walkable_population= walkable_population.agg({'population':'sum'})
        walkable_population.rename(columns={'population':'walkable_population'}, inplace=True)

        pct_walkable= pd.merge(left=state_populations, right=walkable_population, on='STATE', how='left')
        pct_walkable.fillna(0, inplace=True)
        pct_walkable["walkable_population_pct"]= round((pct_walkable.iloc[:,-1] / pct_walkable.iloc[:,1])*100, 2)

        pct_walkable['walkable_population'] = pct_walkable['walkable_population'].astype('int64')
        pct_walkable= pct_walkable.sort_values('walkable_population_pct', ascending=True)

        return pct_walkable

    pct_walkable= mk_wlk(walkability_df)

    @st.cache_data
    def mk_walk_graph(df):
        pct_walkable_graph= px.bar(df, x='walkable_population_pct', y='STATE', 
                                height=1100,
                                title='States/territories by percent of population in "most walkable" blocks',
                                template='plotly_dark')
        pct_walkable_graph.update_layout(xaxis_title="Percent of population with walk index above 15.25")
        pct_walkable_graph.update_traces(marker={"color":'#75b56d'})
        pct_walkable_graph.update_layout(yaxis_title='State')
        return pct_walkable_graph

    st.plotly_chart(mk_walk_graph(pct_walkable), use_container_width=True)

with bottom_row:
    col3, col4 = st.columns(2)
    #write graph of top states on average
       
    @st.cache_data
    def mk_top_10(df):
        by_state_grouped= df.groupby(['STATE'], as_index=False).agg(
            {'NatWalkInd':'mean',
            'population':'sum'})
        by_state_grouped= by_state_grouped.sort_values('NatWalkInd', ascending=False)
        states_10= by_state_grouped.head(10)
        states_10 = states_10.sort_values('NatWalkInd', ascending=True)
        states_10= states_10.rename(columns={'NatWalkInd':'Avg NatWalkInd'})
        return states_10

    states_10= mk_top_10(walkability_df)

    @st.cache_data
    def mk_10_bar(df):
        states_10_bar= px.bar(df, x='Avg NatWalkInd', y='STATE', orientation='h',
                    title='Top 10 states/territories by average walkability score',
                    template='plotly_dark',
                    hover_data=['population'])
        states_10_bar.update_layout(xaxis_range=[0,20],
                            xaxis_title='Average National Walk Index Score',
                            yaxis_title='State')
        states_10_bar.add_vline(x=nationwide_mean, line_width=3, line_dash="dash", line_color="orange",
                    annotation_text='nationwide average')
        states_10_bar.update_traces(marker={"color":'#75b56d'})
        states_10_bar.update_xaxes(title_font=dict(size=12))
        return states_10_bar

    states_10_bar= mk_10_bar(states_10)
    col3.plotly_chart(states_10_bar, use_container_width=True)



#graph CSA's with best transit proximity
    @st.cache_data
    def mk_transit(df):
        transit= df.groupby('CSA_Name', as_index=False)
        transit= transit.agg({'ranked_transit_proximity':'mean',
                            'population':'sum'})
        transit= transit[transit['population'] >= 1000000].sort_values('ranked_transit_proximity', ascending=False).head(10)
        transit= transit.sort_values('ranked_transit_proximity', ascending=True)
        return transit

    transit= mk_transit(walkability_df)

    @st.cache_data
    def get_transit_avg(df):
        transit= df.groupby('CSA_Name', as_index=False)
        transit= transit.agg({'ranked_transit_proximity':'mean',
                            'population':'sum'})
        transit= transit[transit['population'] >= 1000000]
        return transit['ranked_transit_proximity'].mean()

    transit_avg= get_transit_avg(walkability_df)

    @st.cache_data
    def mk_transit_graph(df):
        transit_graph= px.bar(df, y='CSA_Name', x='ranked_transit_proximity',
                            title='Combined statistical areas (>1m) by transit proximity',
                            template="plotly_dark")
        transit_graph.update_layout(xaxis_title="Average transit proximity score",
                                yaxis_title="Combined statistical area")
        transit_graph.update_traces(marker={"color":'#6969b5'})
        transit_graph.add_vline(x=transit_avg, line_width=3, line_dash="dash", line_color="orange",
                    annotation_text='nationwide average')
        transit_graph.update_xaxes(title_font=dict(size=12))
        return transit_graph

    transit_graph= mk_transit_graph(transit)
    col4.plotly_chart(transit_graph, use_container_width=True)
