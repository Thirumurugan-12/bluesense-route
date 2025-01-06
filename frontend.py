import streamlit as st
from route import route
from waypoint import waypoint

st.sidebar.title("Navigation")
page = st.sidebar.radio("Go to", ["Home", "Route optimization" , "Waypoint delivery"])
st.sidebar.image("fedex-logo.svg")


if page == "Home":
    st.title("Home Page")
    st.write("Welcome to the home page!")
elif page == "Route optimization":
    route() 
elif page == "Waypoint delivery":
    waypoint()