import streamlit as st
from datetime import date, timedelta
from src.pipeline import run_phase1, run_phase2
from src.refine import refine
from src.output.pdf import build_trip_pdf
from src.tools.currency import currency_for_country, symbol_for

st.set_page_config(page_title="AI Tour Guide", page_icon="🗺️", layout="centered")

st.markdown("""
<style>
    .block-container { max-width: 760px; }
    div[data-testid="stExpander"] { border: 1px solid #e0e0e0; border-radius: 8px; }
    .budget-fit { background: #e8f5e9; padding: 12px 16px; border-radius: 8px;
                  font-size: 1.05rem; font-weight: 600; color: #1b5e20; margin: 8px 0; }
    .budget-over { background: #fce4ec; padding: 12px 16px; border-radius: 8px;
                   font-size: 1.05rem; font-weight: 600; color: #b71c1c; margin: 8px 0; }
    .place-card { border: 1px solid #e0e0e0; border-radius: 8px; padding: 16px; margin: 8px 0; }
    .place-name { font-size: 1.1rem; font-weight: 600; color: #1f3a5f; }
    .section-label { font-size: 0.85rem; color: #666; margin-top: 4px; }
    .page-badge { display: inline-block; padding: 6px 16px; border-radius: 20px;
                  font-weight: 600; font-size: 0.95rem; margin-bottom: 12px; }
</style>
""", unsafe_allow_html=True)

PAGES = ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "select", "planning", "plan"]

for key in ("phase", "state", "plan_ready", "form", "agent_data"):
    if key not in st.session_state:
        if key == "phase": st.session_state[key] = "p1"
        elif key in ("form", "agent_data"): st.session_state[key] = {}
        elif key == "state": st.session_state[key] = None
        else: st.session_state[key] = False

f = st.session_state.form


def _progress():
    page_num = {"p1": 1, "p2": 2, "p3": 3, "p4": 4, "p5": 5, "p6": 6, "p7": 7}.get(st.session_state.phase, 0)
    if page_num:
        st.progress(page_num / 7)
        st.write(f"**Step {page_num} of 7** — Fill your travel preferences")


# ════════════════════════════════════════
# PAGE 1 — Basic Trip Information
# ════════════════════════════════════════
if st.session_state.phase == "p1":
    st.markdown("""
    <div style="text-align: center; padding: 20px 0 10px 0;">
        <div style="font-size: 3rem;">🗺️</div>
        <h1 style="margin: 0; font-size: 2rem; color: var(--text-color);">AI Tour Guide</h1>
        <p style="font-size: 1.1rem; color: #888; margin: 4px 0 16px 0;">
            Your AI-powered tour planner Agent — real places, real costs, no guesswork.
        </p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
**AI Tour Guide** is a multi-agent travel planner that builds your complete trip — from destination discovery to a downloadable day-by-day plan with real costs.

**Here's how it works:**

1. **Fill a short form** (7 quick pages) — tell us where you're starting from, your dates, who's traveling, your interests, and your budget (optional — the agent can estimate for you).

2. **Get personalized suggestions** — the AI searches real travel data and suggests 3-5 destinations that match your preferences, budget, and travel time. Each suggestion comes with honest pros and cons.

3. **Pick a place, get a full plan** — once you choose, the agent builds:
   - 🚌 **Route** with real bus/train fares and booking links (redBus, MakeMyTrip, AbhiBus)
   - 🏨 **Hotels** with per-night rates and booking links (Booking.com, MakeMyTrip, Goibibo)
   - 📅 **Day-by-day itinerary** with morning, afternoon & evening activities + food recommendations
   - 💰 **Budget breakdown** — all math done in code, never by AI, so the numbers add up correctly
   - 🎒 **Packing list & safety notes** tailored to your destination and season
   - 📄 **Downloadable PDF** of your complete plan

4. **Refine your plan** — not happy? Tell the agent to "make it cheaper", "swap the hotel", or "change day 2" and it adjusts instantly.

**Already have a place in mind?** No problem — tell us and we'll plan that place plus suggest similar nearby alternatives you might love.

**Suggest a state or region?** The agent will recommend the best spots within that area matching your vibe.

💡 **Budget flexibility:** Your plan might come slightly over budget (e.g. ₹1,200 on a ₹1,000 budget) — that's intentional. The agent prioritizes giving you the best experience, not the cheapest skeleton. If it's over, just type **"make it cheaper"** and the agent trims it down instantly. You stay in control.

⚠️ **A note on costs:** Transport fares and hotel prices are grounded in live search data, but actual prices change daily based on booking date, season, bus type, and availability. **What's always accurate:** the route (which bus to take, where it drops you), the hotel names, the itinerary (real places, real attractions), and the booking links. **What may vary:** the exact rupee amount — that's why every fare and hotel comes with a direct booking link (redBus, MakeMyTrip, Booking.com) so you can check the real price before paying. Think of our cost estimates as a reliable starting point, not a final invoice.
    """)
    st.divider()
    _progress()
    st.markdown('<div class="page-badge" style="background:#1565c0;color:white;">📋 Page 1 of 7 — Basic Trip Information</div>', unsafe_allow_html=True)

    with st.form("p1_form"):
        st.markdown("**1. What city will you be travelling from?** *")
        origin_city = st.text_input("Starting city", placeholder="e.g. Delhi, Mumbai, New York",
                                    label_visibility="collapsed")

        st.markdown("**2. Country** *")
        origin_country = st.text_input("Country", placeholder="e.g. India, USA, Japan",
                                       label_visibility="collapsed")

        st.markdown("**3. Travel dates** *")
        d1, d2 = st.columns(2)
        with d1:
            start_date = st.date_input("Departure date")
        with d2:
            end_date = st.date_input("Return date")

        st.markdown("**4. Travelers** *")
        t1, t2 = st.columns(2)
        with t1:
            num_travelers = st.number_input("Number of travelers", min_value=1, max_value=20, value=2)
        with t2:
            group_type = st.selectbox("Travel group type", ["Solo", "Couple", "Friends", "Family", "Colleagues"])

        st.markdown("**5. Budget** (optional — leave 0 and the agent estimates for you)")
        total_budget = st.number_input("Total trip budget", min_value=0, step=1000, value=0)
        if total_budget > 0:
            budget_scope = st.selectbox("Budget is for", ["whole group", "per person"])
        else:
            budget_scope = "whole group"
        st.caption("ℹ️ If this budget is too low, the agent will tell you honestly and plan the cheapest realistic version.")

        st.markdown("**6. Preferred transport mode** *")
        transport_mode = st.selectbox("Transport mode", ["Bus", "Train", "Flight", "Car", "Cheapest", "Any"],
                                      label_visibility="collapsed")

        st.markdown(f"**7. When do you want to board your {transport_mode.lower()}?** (optional)")
        tt1, tt2 = st.columns(2)
        with tt1:
            st.caption("Going — departure day")
            departure_timing = st.selectbox("Departure boarding time",
                                            ["Any time",
                                             "Early Morning (4 AM – 8 AM)",
                                             "Morning (8 AM – 12 PM)",
                                             "Afternoon (12 PM – 4 PM)",
                                             "Evening (4 PM – 8 PM)",
                                             "Night (8 PM – 12 AM)",
                                             "Late Night (12 AM – 4 AM)"],
                                            label_visibility="collapsed")
        with tt2:
            st.caption("Return — coming back day")
            return_timing = st.selectbox("Return boarding time",
                                         ["Any time",
                                          "Early Morning (4 AM – 8 AM)",
                                          "Morning (8 AM – 12 PM)",
                                          "Afternoon (12 PM – 4 PM)",
                                          "Evening (4 PM – 8 PM)",
                                          "Night (8 PM – 12 AM)",
                                          "Late Night (12 AM – 4 AM)"],
                                         label_visibility="collapsed")
        st.caption(f"ℹ️ The agent will search for {transport_mode.lower()} options matching your preferred boarding time.")

        next1 = st.form_submit_button("Next → Destination Preferences", type="primary", use_container_width=True)

    if next1:
        errors = []
        if not origin_city.strip():
            errors.append("Starting city is required.")
        if not origin_country.strip():
            errors.append("Country is required.")
        if end_date <= start_date:
            errors.append("Return date must be after departure date.")
        if num_travelers < 1:
            errors.append("At least 1 traveler is required.")
        if errors:
            for e in errors:
                st.error(e)
        else:
            code = currency_for_country(origin_country)
            sym = symbol_for(code)
            trip_days = (end_date - start_date).days
            st.success(f"🪙 Currency: **{code}** ({sym})  |  📅 Trip: **{start_date}** to **{end_date}** ({trip_days} days, {trip_days - 1} nights)")
            f.update({"origin_city": origin_city, "origin_country": origin_country,
                      "start_date": str(start_date), "end_date": str(end_date),
                      "num_travelers": num_travelers, "group_type": group_type,
                      "total_budget": total_budget, "budget_scope": budget_scope,
                      "transport_mode": transport_mode,
                      "departure_timing": departure_timing, "return_timing": return_timing})
            st.session_state.phase = "p2"
            st.rerun()


# ════════════════════════════════════════
# PAGE 2 — Destination Preferences
# ════════════════════════════════════════
elif st.session_state.phase == "p2":
    _progress()
    st.markdown('<div class="page-badge" style="background:#0277bd;color:white;">🌍 Page 2 of 7 — Destination Preferences</div>', unsafe_allow_html=True)

    st.caption(f"From **{f.get('origin_city')}** · {f.get('start_date')} to {f.get('end_date')} · {f.get('transport_mode')}")

    # radio OUTSIDE the form so it updates immediately
    st.markdown("**1. Do you have a destination in mind?**")
    has_place = st.radio("Destination choice",
                         ["No — AI will suggest the best options for me",
                          "Yes — I have a place in mind"],
                         label_visibility="collapsed",
                         key="has_place_radio")

    place_in_mind = ""
    if has_place.startswith("Yes"):
        place_in_mind = st.text_input("Which place or region? (state, city, or specific place)",
                                      placeholder="e.g. Himachal Pradesh, Manali, Jibhi, Kasol",
                                      key="place_input")
        if place_in_mind:
            st.caption(f"✅ The agent will suggest **{place_in_mind}** plus similar nearby places that match your preferences.")

    with st.form("p2_form"):
        st.markdown("**2. Type of destination**")
        destination_type = st.selectbox("Destination type", ["Suggest by Agent", "Mountains", "Beach", "City",
                                                              "Offbeat village", "Wildlife", "Desert", "Lake / River"],
                                        label_visibility="collapsed")

        st.markdown("**3. Geographical region preference**")
        region_preference = st.selectbox("Region", ["Suggest by Agent", "North India", "South India",
                                                     "East India", "West India", "Northeast India",
                                                     "Central India", "International"],
                                         label_visibility="collapsed")

        st.markdown("**4. Preferred weather during trip**")
        weather_pref = st.selectbox("Weather", ["No Preference", "Cold", "Pleasant", "Hot", "Snow", "Rainy"],
                                    label_visibility="collapsed")

        st.markdown("**5. Place preference**")
        place_preference = st.radio("Place style", ["A Mix of Both", "Popular Tourist Places", "Hidden Gems"],
                                    label_visibility="collapsed", horizontal=True)

        st.markdown("**6. Max travel time comfortable**")
        max_travel = st.selectbox("Max travel hours", ["No Limit", "4 hours", "6 hours", "8 hours",
                                                        "10 hours", "12 hours", "16 hours"],
                                  label_visibility="collapsed")

        c1, c2 = st.columns(2)
        with c1:
            back2 = st.form_submit_button("← Back")
        with c2:
            next2 = st.form_submit_button("Next → Activities", type="primary")

    if back2:
        st.session_state.phase = "p1"; st.rerun()
    if next2:
        final_place = place_in_mind.strip() if has_place.startswith("Yes") else ""
        if has_place.startswith("Yes") and not final_place:
            st.error("You selected 'Yes' but didn't enter a place. Please type a place or select 'No'.")
            st.stop()
        max_hrs = None if max_travel == "No Limit" else int(max_travel.split()[0])
        f.update({"place_in_mind": final_place, "destination_type": destination_type,
                  "region_preference": region_preference, "weather_pref": weather_pref,
                  "place_preference": place_preference, "max_travel_hours": max_hrs})
        st.session_state.phase = "p3"; st.rerun()


# ════════════════════════════════════════
# PAGE 3 — Activities & Interests
# ════════════════════════════════════════
elif st.session_state.phase == "p3":
    _progress()
    st.markdown('<div class="page-badge" style="background:#c62828;color:white;">🎯 Page 3 of 7 — Activities & Interests</div>', unsafe_allow_html=True)

    with st.form("p3_form"):
        st.markdown("**1. Activities you are interested in** *")
        activities = st.multiselect("Activities", ["Nature & Scenic Views", "Relaxation & Wellness",
                                                    "Adventure Sports", "Wildlife Safari", "Food Exploration",
                                                    "Shopping", "Historical Sites", "Religious / Spiritual",
                                                    "Cultural Experiences", "Museums", "Nightlife",
                                                    "Romantic Experiences", "Photography", "Trekking / Hiking",
                                                    "Water Sports", "Workation"],
                                    label_visibility="collapsed")

        st.markdown("Don't see what you're looking for? Type your own activity here (optional)")
        custom_activities = st.text_input("Custom activities", placeholder="e.g. Stargazing, Pottery classes, Local festivals",
                                          label_visibility="collapsed")

        st.markdown("**2. Your highest priority activity**")
        all_activity_options = ["No specific priority", "Nature & Scenic Views", "Relaxation & Wellness",
                                "Adventure Sports", "Wildlife Safari", "Food Exploration",
                                "Shopping", "Historical Sites", "Religious / Spiritual",
                                "Cultural Experiences", "Museums", "Nightlife",
                                "Romantic Experiences", "Photography", "Trekking / Hiking",
                                "Water Sports", "Workation"]
        priority_activity = st.selectbox("Priority activity", all_activity_options, label_visibility="collapsed")

        st.markdown("**3. Activities you do NOT want**")
        avoid_activities = st.text_input("Activities to avoid", placeholder="e.g. Nightlife, Adventure Sports",
                                         label_visibility="collapsed")

        c1, c2 = st.columns(2)
        with c1:
            back3 = st.form_submit_button("← Back")
        with c2:
            next3 = st.form_submit_button("Next → Accommodation", type="primary")

    if back3:
        st.session_state.phase = "p2"; st.rerun()
    if next3:
        if not activities and not custom_activities.strip():
            st.error("Please select at least one activity or type your own.")
            st.stop()
        vibe = ", ".join(activities)
        if custom_activities:
            vibe += f", {custom_activities}"
        f.update({"trip_vibe": vibe, "custom_activities": custom_activities,
                  "priority_activity": priority_activity if priority_activity != "No specific priority" else "",
                  "activities_to_avoid": avoid_activities})
        st.session_state.phase = "p4"; st.rerun()


# ════════════════════════════════════════
# PAGE 4 — Accommodation
# ════════════════════════════════════════
elif st.session_state.phase == "p4":
    _progress()
    st.markdown('<div class="page-badge" style="background:#1565c0;color:white;">🏨 Page 4 of 7 — Accommodation</div>', unsafe_allow_html=True)

    with st.form("p4_form"):
        st.markdown("**1. Accommodation type**")
        property_type = st.selectbox("Property type", ["Hotel", "Homestay", "Hostel", "Resort", "Any"],
                                     label_visibility="collapsed")

        agent_suggest_hotel = st.checkbox("Let the agent suggest hotel budget (recommended)", value=True)

        hotel_min, hotel_max = 0, 0
        if not agent_suggest_hotel:
            h1, h2 = st.columns(2)
            with h1:
                hotel_min = st.number_input("Min per night", min_value=0, value=1000, step=500)
            with h2:
                hotel_max = st.number_input("Max per night", min_value=0, value=3000, step=500)

        st.markdown("**2. Preferred room type**")
        bed_type = st.selectbox("Room type", ["Double", "Twin", "Single", "Any"], label_visibility="collapsed")

        st.markdown("**3. Minimum hotel rating**")
        min_rating = st.slider("Min rating", 1.0, 5.0, 3.0, 0.5, label_visibility="collapsed")

        st.markdown("**4. Important amenities**")
        amenities = st.multiselect("Amenities", ["Wi-Fi", "AC", "Breakfast included", "Parking",
                                                   "Hot water", "Room service", "Swimming pool",
                                                   "Pet-friendly", "Kitchen"],
                                   label_visibility="collapsed")

        preferred_area = st.text_input("Preferred location/area (optional)",
                                       placeholder="e.g. near market, quiet, lakeside")

        non_couples = st.selectbox("Non-couples sharing rooms?", ["share", "separate"])

        c1, c2 = st.columns(2)
        with c1:
            back4 = st.form_submit_button("← Back")
        with c2:
            next4 = st.form_submit_button("Next → Food Preferences", type="primary")

    if back4:
        st.session_state.phase = "p3"; st.rerun()
    if next4:
        f.update({"hotel_type": property_type.lower(),
                  "hotel_per_night_min": hotel_min, "hotel_per_night_max": hotel_max,
                  "agent_suggest_hotel": agent_suggest_hotel,
                  "bed_type": bed_type.lower(), "min_rating": min_rating,
                  "amenities": ", ".join(amenities), "preferred_area": preferred_area,
                  "non_couples_sharing": non_couples})
        st.session_state.phase = "p5"; st.rerun()


# ════════════════════════════════════════
# PAGE 5 — Food Preferences
# ════════════════════════════════════════
elif st.session_state.phase == "p5":
    _progress()
    st.markdown('<div class="page-badge" style="background:#e65100;color:white;">🍜 Page 5 of 7 — Food Preferences</div>', unsafe_allow_html=True)

    with st.form("p5_form"):
        st.markdown("**1. Food preferences** *")
        food_pref = st.multiselect("Food preferences", ["No Preference", "Vegetarian", "Non-Vegetarian",
                                                         "Vegan", "Jain", "Halal", "Local Cuisine"],
                                   default=["No Preference"], label_visibility="collapsed")

        st.markdown("**2. Food allergies (if any)**")
        food_allergies = st.text_input("Food allergies", placeholder="e.g. nuts, dairy",
                                       label_visibility="collapsed")

        st.markdown("**3. Foods to avoid (if any)**")
        foods_to_avoid = st.text_input("Foods to avoid", placeholder="e.g. spicy food, seafood",
                                       label_visibility="collapsed")

        c1, c2 = st.columns(2)
        with c1:
            back5 = st.form_submit_button("← Back")
        with c2:
            next5 = st.form_submit_button("Next → Special Requirements", type="primary")

    if back5:
        st.session_state.phase = "p4"; st.rerun()
    if next5:
        if not food_pref:
            st.error("Please select at least one food preference.")
            st.stop()
        f.update({"food_pref": ", ".join(food_pref),
                  "food_allergies": food_allergies, "foods_to_avoid": foods_to_avoid})
        st.session_state.phase = "p6"; st.rerun()


# ════════════════════════════════════════
# PAGE 6 — Special Requirements
# ════════════════════════════════════════
elif st.session_state.phase == "p6":
    _progress()
    st.markdown('<div class="page-badge" style="background:#6a1b9a;color:white;">♿ Page 6 of 7 — Special Requirements</div>', unsafe_allow_html=True)

    with st.form("p6_form"):
        st.caption("All optional — skip if not applicable")

        c1, c2 = st.columns(2)
        with c1:
            senior = st.checkbox("Senior citizens travelling")
            children = st.checkbox("Children travelling")
            mobility = st.checkbox("Mobility restrictions")
        with c2:
            wheelchair = st.checkbox("Wheelchair-friendly locations needed")

        st.markdown("**Medical considerations**")
        medical = st.text_area("Medical notes", placeholder="e.g. heart condition, diabetes",
                               label_visibility="collapsed")

        st.markdown("**Special requests**")
        special_req = st.text_area("Special requests", placeholder="e.g. Celebrating anniversary, need baby cot, less crowd, safe in monsoon",
                                   label_visibility="collapsed")

        c1, c2 = st.columns(2)
        with c1:
            back6 = st.form_submit_button("← Back")
        with c2:
            next6 = st.form_submit_button("Next → Review & Submit", type="primary")

    if back6:
        st.session_state.phase = "p5"; st.rerun()
    if next6:
        special_parts = []
        if senior: special_parts.append("senior citizens traveling")
        if children: special_parts.append("children traveling")
        if mobility: special_parts.append("mobility restrictions")
        if wheelchair: special_parts.append("wheelchair-friendly needed")
        if medical: special_parts.append(medical)
        if special_req: special_parts.append(special_req)
        f.update({"senior_citizens": senior, "children_traveling": children,
                  "mobility_restrictions": mobility, "wheelchair_needed": wheelchair,
                  "medical_considerations": medical,
                  "special_requirements": "; ".join(special_parts)})
        st.session_state.phase = "p7"; st.rerun()


# ════════════════════════════════════════
# PAGE 7 — Review & Submit
# ════════════════════════════════════════
elif st.session_state.phase == "p7":
    _progress()
    st.markdown('<div class="page-badge" style="background:#2e7d32;color:white;">📋 Page 7 of 7 — Review & Submit</div>', unsafe_allow_html=True)

    st.divider()
    st.subheader("📋 Your Trip Summary")

    code = currency_for_country(f.get("origin_country", ""))
    sym = symbol_for(code)

    # compute duration correctly
    try:
        s_date = date.fromisoformat(f["start_date"])
        e_date = date.fromisoformat(f["end_date"])
        trip_days = (e_date - s_date).days
    except Exception:
        trip_days = 0

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("📍 From", f.get("origin_city", ""))
    c2.metric("📅 Departure", f.get("start_date", ""))
    c3.metric("🔙 Return", f.get("end_date", ""))
    c4.metric("⏱ Duration", f"{trip_days} days")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("👥 Travelers", f.get("num_travelers", ""))
    c2.metric("🤝 Group", f.get("group_type", ""))
    budget_val = f.get("total_budget", 0)
    c3.metric("💰 Budget", f"{sym}{budget_val:,.0f}" if budget_val > 0 else "Agent estimates")
    c4.metric("🚌 Transport", f.get("transport_mode", ""))

    # show timing
    st.markdown(f"**Departure timing:** {f.get('departure_timing', 'Any')} on {f.get('start_date', '')}")
    st.markdown(f"**Return timing:** {f.get('return_timing', 'Any')} on {f.get('end_date', '')}")

    st.info("🔍 **Next:** AI discovers the **Top 5 destinations**. You pick one, then we build your complete plan.")

    c1, c2 = st.columns(2)
    with c1:
        if st.button("← Back"):
            st.session_state.phase = "p6"; st.rerun()
    with c2:
        if st.button("🔍 Discover My Top 5 Destinations!", type="primary"):
            import copy
            # freeze form data — agents get a copy, never the original
            frozen = copy.deepcopy(f)
            st.session_state["frozen_form"] = frozen
            raw = copy.deepcopy(frozen)
            raw.setdefault("pace", "relaxed")
            raw.setdefault("purpose", frozen.get("priority_activity", ""))
            with st.spinner("🔍 Searching for the perfect destinations..."):
                result = run_phase1(raw)
            if result.get("error"):
                st.error(result["error"])
            else:
                st.session_state.state = result
                st.session_state.phase = "select"
                st.rerun()


# ════════════════════════════════════════
# PHASE: SELECT A PLACE
# ════════════════════════════════════════
elif st.session_state.phase == "select":
    state = st.session_state.state
    suggestions = state["suggestions"]["suggestions"]

    if not suggestions and state["suggestions"].get("top_recommendation"):
        st.session_state.state["selected_place"] = state["suggestions"]["top_recommendation"]
        st.session_state.phase = "planning"
        st.rerun()

    if not suggestions:
        st.error("No feasible destinations found. Try adjusting your dates, budget, or transport mode.")
        if st.button("Try again"):
            st.session_state.phase = "p1"
            st.session_state.state = None
            st.rerun()
        st.stop()

    st.title("🗺️ Top Destinations For You")
    st.caption(f"🏆 Top pick: **{state['suggestions']['top_recommendation']}** — "
               f"{state['suggestions']['reasoning']}")

    for s in suggestions:
        st.markdown(f"""<div class="place-card">
            <div class="place-name">{s['name']} <span style="color:#888;">({s['region']})</span></div>
            <div class="section-label">Why it fits</div>{s['why_it_fits']}
            <div class="section-label">Best for</div>{s['best_for']}
            <div class="section-label">Honest downside</div>{s['possible_downside']}
        </div>""", unsafe_allow_html=True)

    options = [s["name"] for s in suggestions]
    choice = st.radio("Choose your destination", options, index=0)

    c1, c2, c3 = st.columns(3)
    with c1:
        if st.button("← Start over"):
            st.session_state.phase = "p1"; st.session_state.state = None; st.rerun()
    with c2:
        if st.button("🔄 Suggest different places"):
            import copy

            old_names = [s["name"] for s in suggestions]
            ad = st.session_state.agent_data
            prev_excluded = ad.get("excluded_places", [])
            all_excluded = prev_excluded + old_names
            ad["excluded_places"] = all_excluded

            if len(all_excluded) > 12:
                st.warning("You've seen many options. Try changing your preferences (activities, destination type, region) for genuinely different results.")
            else:
                try:
                    import os
                    if os.path.exists(".search_cache.json"):
                        os.remove(".search_cache.json")
                except Exception:
                    pass

                round_num = len(all_excluded) // 3
                angle_hints = [
                    "offbeat lesser known",
                    "underrated peaceful",
                    "trending new hidden gem",
                    "budget friendly scenic",
                ]
                hint = angle_hints[round_num % len(angle_hints)]

                # use frozen form data, never modify the original
                raw = copy.deepcopy(st.session_state.get("frozen_form", f))
                raw.setdefault("pace", "relaxed")
                raw.setdefault("purpose", raw.get("priority_activity", ""))
                raw["_excluded_places"] = all_excluded
                raw["_search_hint"] = hint

                with st.spinner("Finding different destinations..."):
                    result = run_phase1(raw)
                if result.get("error"):
                    st.error("Couldn't find more options. Try changing your preferences.")
                else:
                    st.session_state.state = result
                    st.rerun()
    with c3:
        if st.button("Plan this trip →", type="primary"):
            st.session_state.state["selected_place"] = choice
            st.session_state.phase = "planning"
            st.rerun()


# ════════════════════════════════════════
# PHASE: PLANNING (auto-run)
# ════════════════════════════════════════
elif st.session_state.phase == "planning":
    place = st.session_state.state.get("selected_place", "")
    st.title(f"⏳ Planning: {place}")
    st.write("Building your route, itinerary, hotels, and budget...")

    hotel_prefs = {
        "property_type": f.get("hotel_type", "any"),
        "non_couples_sharing": f.get("non_couples_sharing", "share"),
        "hotel_per_night_min": f.get("hotel_per_night_min", 0) if not f.get("agent_suggest_hotel") else None,
        "hotel_per_night_max": f.get("hotel_per_night_max", 0) if not f.get("agent_suggest_hotel") else None,
        "preferred_area": f.get("preferred_area", ""),
        "amenities": f.get("amenities", ""),
        "min_rating": f.get("min_rating", 0),
    }

    with st.spinner("Planning your trip (route → itinerary → hotels → budget)..."):
        result = run_phase2(st.session_state.state, place, hotel_prefs)

    if result.get("error"):
        st.error(result["error"])
        if st.button("Try a different place"):
            st.session_state.phase = "select"; st.rerun()
    else:
        st.session_state.state = result
        st.session_state.plan_ready = True
        st.session_state.phase = "plan"
        st.rerun()


# ════════════════════════════════════════
# PHASE: SHOW THE PLAN
# ════════════════════════════════════════
elif st.session_state.phase == "plan":
    s = st.session_state.state
    sym = s.get("currency_symbol", "")
    place = s.get("selected_place", "")

    st.title(f"🗺️ Trip Plan: {place}")

    budget = s.get("budget", {})
    css_class = "budget-fit" if budget.get("fits_budget") else "budget-over"
    st.markdown(f'<div class="{css_class}">{s.get("budget_headline", "")}</div>', unsafe_allow_html=True)

    route = s.get("route", {})
    if route.get("legs"):
        st.subheader("🚌 Getting There")
        for leg in route["legs"]:
            if leg.get("cost_min") is not None:
                unit = "/vehicle" if leg.get("per_vehicle") else "/person"
                cost = f"~{sym}{leg['cost_min']}–{sym}{leg['cost_max']}{unit}"
            else:
                cost = leg.get("note") or "verify before booking"
            st.markdown(f"**{leg['from_place']}** → **{leg['to_place']}** by {leg['mode']}  —  {cost}")
            links = leg.get("booking_links", [])
            if links:
                link_text = "  |  ".join([f"[{l['site']}]({l['url']})" for l in links])
                st.markdown(f"Book: {link_text}")

    st.subheader("🏨 Where to Stay")
    rc = s.get("room_config", {})
    if rc:
        st.write(f"**Rooms:** {rc.get('description', '')} ({rc.get('bed_types', '')})")
    for h in s.get("hotels", []):
        price = f" — {sym}{h['per_night_min']}/night" if h.get("per_night_min") else ""
        st.write(f"• {h['name']}{price}")
    h_links = s.get("hotel_booking_links", [])
    if h_links:
        link_text = "  |  ".join([f"[{l['site']}]({l['url']})" for l in h_links])
        st.markdown(f"Book stays: {link_text}")

    st.subheader("📅 Day-by-Day Itinerary")
    for day in s.get("itinerary", []):
        with st.expander(f"{day['day_label']} ({day['date']})", expanded=True):
            for a in day["activities"]:
                st.write(f"• {a}")

    st.subheader("💰 Budget Breakdown")
    if budget.get("items"):
        for item in budget["items"]:
            c1, c2 = st.columns([3, 1])
            c1.write(f"{item['item']}  *({item.get('note', '')})*")
            c2.write(f"**{sym}{item['amount']}**")
        st.divider()
        c1, c2 = st.columns([3, 1])
        c1.write("**TOTAL**")
        c2.write(f"**{sym}{budget['total']}**")

    cl, cr = st.columns(2)
    with cl:
        st.subheader("🎒 Packing List")
        for p in s.get("packing_list", []):
            st.write(f"• {p}")
    with cr:
        st.subheader("⚠️ Safety Notes")
        for n in s.get("safety_notes", []):
            st.write(f"• {n}")

    st.subheader("📌 What to Book First")
    for b in s.get("booking_order", []):
        st.write(f"• {b}")

    if s.get("map_link"):
        st.markdown(f"[🗺️ Open {place} on the map]({s['map_link']})")

    st.divider()
    pdf_path = "trip_plan.pdf"
    build_trip_pdf(s, pdf_path)
    with open(pdf_path, "rb") as fp:
        st.download_button("📥 Download Trip Plan (PDF)", fp, file_name=f"trip_plan_{place}.pdf",
                           mime="application/pdf", use_container_width=True)

    st.divider()
    st.subheader("Want to change something?")
    with st.form("refine_form"):
        refine_cmd = st.text_input("Type a change",
                                   placeholder="make it cheaper / swap the hotel / change day 2...")
        refine_btn = st.form_submit_button("Apply change", type="primary")

    if refine_btn and refine_cmd.strip():
        with st.spinner("Adjusting..."):
            updated, msg = refine(s, refine_cmd.strip())
        st.session_state.state = updated
        st.success(msg)
        st.rerun()

    if st.button("🔄 Start a new trip"):
        st.session_state.phase = "p1"
        st.session_state.state = None
        st.session_state.form = {}
        st.session_state.agent_data = {}
        st.session_state.plan_ready = False
        if "frozen_form" in st.session_state:
            del st.session_state["frozen_form"]
        st.rerun()