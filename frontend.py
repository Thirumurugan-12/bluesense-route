import streamlit as st
from route import route
from waypoint import waypoint
from streamlit_pdf_viewer import pdf_viewer


st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Route optimization" , "Waypoint delivery"])
st.sidebar.image("fedex-logo.svg")
# st.set_page_config(page_title="Fedex", page_icon=":truck:", layout="wide")

if page == "Home":
    st.title("Fedex Route Optimization")
    st.write("Team BlueStar")
    ss = "fedxppt.pdf"
    pdf_viewer(input=ss, width=700)
elif page == "Route optimization":
    route() 
elif page == "Waypoint delivery":
    waypoint()