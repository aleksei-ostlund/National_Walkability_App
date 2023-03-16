# walkability_app.py

import pandas as pd
import streamlit as st
import plotly.express as px

walkability_df= pd.read_csv("walkability_2021.csv")

interest_columns= ['OBJECTID', 'STATEFP', 'COUNTYFP', 'TRACTCE', 'BLKGRPCE','CSA', 'CSA_Name','CBSA_Name',
                   'CBSA_POP', 'TotPop', 'Pct_AO0', 'Pct_AO1', 'Pct_AO2p', 'NatWalkInd']

walkability_df_condensed= walkability_df[interest_columns]

#get html table of state FIPS codes
statefp_df= pd.read_html('https://www.bls.gov/respondents/mwr/electronic-data-interchange/appendix-d-usps-state-abbreviations-and-fips-codes.htm')

statefp_df= statefp_df[1]
statefp_df.columns = statefp_df.iloc[0]
statefp_df= statefp_df.iloc[1:]
#separate two sets of three columns and stack them to get proper table
statefp_df1= statefp_df.iloc[:,:3]
statefp_df2= statefp_df.iloc[:, 3:]
statefp_df = pd.concat([statefp_df1, statefp_df2])
statefp_df.reset_index(inplace=True)
statefp_df= statefp_df.iloc[:53,1:]
#rename columns to match main table for merge
statefp_df.rename(columns={'FIPS  Code':'STATEFP','State': 'STATE','Postal  Abbr..': 'PC'}, inplace=True)
statefp_df['STATEFP']= statefp_df['STATEFP'].astype('int64')

#merge tables to get state names
walkability_df_condensed= pd.merge(left=walkability_df_condensed, right=statefp_df, on='STATEFP')

#read in html table to get FIPS codes for counties
county_fips= pd.read_html('https://en.wikipedia.org/wiki/List_of_United_States_FIPS_codes_by_county')
county_fips= county_fips[1]

#rename columns to prepare for merge
county_fips.rename(columns={'FIPS':'SCFP', 'County or equivalent':'COUNTY'}, inplace=True)

#add missing filler zeros to FIPS codes
county_fips['SCFP']= county_fips['SCFP'].astype('str').str.zfill(5)
county_fips= county_fips.iloc[:, :2]

#combined FIPS codes include filler zeroes in both state and county FIPS
#these were not present due to int datatype and need to be filled in
walkability_df_condensed['STATEFP']= (walkability_df_condensed['STATEFP']
                                      .astype('string')
                                      .str.zfill(2))
walkability_df_condensed['COUNTYFP']= (walkability_df_condensed['COUNTYFP']
                                      .astype('string')
                                      .str.zfill(3))

#concatenate the state and county fips
walkability_df_condensed['SCFP']= walkability_df_condensed['STATEFP'] + walkability_df_condensed['COUNTYFP']

#join tables on combined state and county FIPS to add county names
walkability_df_condensed= pd.merge(left=walkability_df_condensed, right=county_fips, on='SCFP', how='left')

#take subset of data with counties that are not null
non_na_counties = walkability_df_condensed[walkability_df_condensed['COUNTY'].notna()]

#remove footnote brackets that came from html table
non_na_counties.loc[non_na_counties['COUNTY'].str.contains('\['),'COUNTY'] = (non_na_counties['COUNTY']
                                                                              .str
                                                                              .slice(stop=-3))

nationwide_mean= non_na_counties['NatWalkInd'].mean()

#group by state/county and get mean walk score
by_county_grouped= non_na_counties.groupby(['STATE','COUNTY'], as_index=False).agg(
    {'NatWalkInd':'mean',
     'TotPop':'sum'})


#select counties in NY state
ny_counties= by_county_grouped[by_county_grouped['STATE']=='New York'].iloc[:60].sort_values('NatWalkInd', ascending=False)
ny_10= ny_counties.head(10)
ny_10['NatWalkInd']= ny_10['NatWalkInd'].round(2)
ny_10.rename(columns={'NatWalkInd':'Avg NatWalkInd', 'TotPop':'Population'}, inplace=True)

#group by state and get mean walk score
by_state_grouped= non_na_counties.groupby(['STATE'], as_index=False).agg(
    {'NatWalkInd':'mean',
     'TotPop':'sum'}).sort_values('NatWalkInd', ascending=False)
states_10= by_state_grouped.head(10).sort_values('STATE')
states_10= states_10.rename(columns={'NatWalkInd':'Avg NatWalkInd', 'TotPop':'Population'})

#create bar graph
states_10_bar= px.bar(states_10, x='Avg NatWalkInd', y='STATE', orientation='h',
                 title='Top ten states by average walkability score',
                 template='plotly_dark',
                 hover_data=['Population'])
states_10_bar.update_layout(xaxis_range=[0,20],
                        xaxis_title='Average National Walk Index Score',
                        yaxis_title='State')
states_10_bar.add_vline(x=nationwide_mean, line_width=3, line_dash="dash", line_color="orange",
                   annotation_text='nationwide average')


#streamlite app

hide_streamlit_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            </style>
            """
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

st.header("Insights from the EPA\'s National Walkability Index")

natwalkind_cats= pd.DataFrame(
    {'Classification': ['Rural Area', 
                        'Suburban Residential Area',
                        'Historic Main Street/Downtown', 
                        'City Center/Suburban Town Center'], 
    'National Walk Index Score' : ['<8.3', 
                                   '8.3 to 13.6', 
                                   '13.7 to 17.4', 
                                   '>17.4']})
natwalkind_cats.set_index('Classification', inplace=True)

if st.button('See the categories', type='primary'):
    # st.write('Rural Area: <8.3')
    # st.write('Suburban Residential Area: 8.3 - 13.6')
    # st.write('Historic Main Street/Downtown: 13.7 - 17.4')
    # st.write('City Center/Suburban Town Center: >17.4')
    st.write(natwalkind_cats)

st.write('The nationwide average is {}'.format(round(nationwide_mean, 2)),
         states_10_bar)