from cdp_backend.pipeline import ingestion_models
from datetime import datetime

event = ingestion_models.EventIngestionModel(
    body=ingestion_models.Body("COMMITTEE ON COUNCIL", is_active=True),
    sessions=[
        ingestion_models.Session(
            video_uri="https://atlantacityga.iqm2.com/Citizens/SplitView.aspx?Mode=Video&MeetingID=3587&Format=Minutes",
            session_index=0,
            session_datetime=datetime.utcnow()
        )
    ],
    event_minutes_items = [
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("CALL TO ORDER")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("INTRODUCTION OF MEMBERS")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("ADOPTION OF AGENDA"),
            # unsure about matter name
            decision = "ADOPTED",
            votes = [
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Andrea L. Boone",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 10",
                            roles = ingestion_models.Role("Chair"))
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Amir R Farokhi",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 2"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Dustin Hillis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 9"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Antonio Lewis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 12"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Mary Norwood",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 8"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Howard Shook",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 7"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Matt Westmoreland",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Post 2 At-Large"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                )      
            ]
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("APPROVAL OF MINUTES"),
            decision = "ADOPTED",
            votes = [
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Andrea L. Boone",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 10",
                            roles = ingestion_models.Role("Chair"))
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Amir R Farokhi",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 2"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Dustin Hillis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 9"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Antonio Lewis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 12"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Mary Norwood",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 8"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Howard Shook",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 7"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Matt Westmoreland",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Post 2 At-Large"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                )      
            ]
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("ADOPTION OF FULL COUNCIL AGENDA"),
            decision = "ADOPTED",
            votes = [
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Andrea L. Boone",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 10",
                            roles = ingestion_models.Role("Chair"))
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Amir R Farokhi",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 2"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Dustin Hillis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 9"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Antonio Lewis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 12"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Mary Norwood",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 8"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Howard Shook",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 7"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Matt Westmoreland",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Post 2 At-Large"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                )      
            ]
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("PUBLIC COMMENT")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("COMMUNICATION(S)"),
            matter = #How to add more matters
                ingestion_models.Matter(
                "22-C-5024 (1)", 
                matter_type = "COMMUNICATION",
                title = "A COMMUNICATION FROM TONYA GRIER, COUNTY CLERK TO THE FULTON COUNTY BOARD OF COMMISSIONERS, SUBMITTING THE APPOINTMENT OF MS. NATALIE HORNE TO THE ATLANTA BELTLINE TAX ALLOCATION DISTRICT (TAD) ADVISORY COMMITTEE. THIS APPOINTMENT IS FOR A TERM OF TWO (2) YEARS.",
                result_status = "FAVORABLE",
                sponsors = [
                    # unsure 
                    ingestion_models.Person(
                        "TONYA GRIER",
                        is_active = "true",
                        seat = ingestion_models.Seat("COUNTY CLERK")
                    )
                ]
            ),
            decision = "FAVORABLE",
            votes = [
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Andrea L. Boone",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 10",
                            roles = ingestion_models.Role("Chair"))
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Amir R Farokhi",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 2"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Dustin Hillis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 9"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Antonio Lewis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 12"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Mary Norwood",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 8"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Howard Shook",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 7"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Matt Westmoreland",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Post 2 At-Large"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                )      
            ]
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("RESOLUTION(S)"),
            matter = 
                ingestion_models.Matter(
                "22-R-3404 (8)", 
                matter_type = "RESOLUTION(S)",
                title = "A RESOLUTION BY COMMITTEE ON COUNCIL A RESOLUTION TO SUNSET CERTAIN BOARDS, AUTHORITIES, COMMISSIONS AND OTHER GROUPS, CREATED BY ACTION OF THE ATLANTA CITY COUNCIL, BECAUSE SUCH BOARDS, AUTHORITIES, COMMISSIONS, AND OTHER GROUPS HAVE ACCOMPLISHED THE PURPOSES FOR WHICH THEY WERE CREATED, WHOSE AUTHORIZED TERM HAS EXPIRED, AND/OR ARE NO LONGER REQUIRED; AND FOR OTHER PURPOSES.",
                result_status = "FAVORABLE"
                # sponsors be the committe on council?
            ),
            decision = "FAVORABLE",
            votes = [
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Andrea L. Boone",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 10",
                            roles = ingestion_models.Role("Chair"))
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Amir R Farokhi",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 2"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Dustin Hillis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 9"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Antonio Lewis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 12"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Mary Norwood",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 8"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Howard Shook",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 7"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Matt Westmoreland",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Post 2 At-Large"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                )      
            ]
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("PAPER(S) HELD IN COMMITTEE"),
            matter = #How to add more matters
                ingestion_models.Matter(
                "22-O-1150 (9)", 
                matter_type = "PAPER(S) HELD IN COMMITTEE",
                title = "A SUBSTITUTE ORDINANCE BY COMMITTEE ON COUNCIL TO AMEND CITY OF ATLANTA CODE OF ORDINANCES SECTION 66-2 \"PRECINCT BOUNDARY LINES AND POLLING PLACES\" BY AMENDING THE 2017 PRECINCTS AND POLLING PLACES ORDINANCE IN FULTON COUNTY PRECINCTS 02L2, 03I, 03C, 06R, 07M, 08A, 08G AND 11R DUE TO FACILITIES UNABLE TO ACCOMMODATE POLLING OPERATIONS; FACILITY UNDERGOING RENOVATIONS AND FACILITY VOTING SITE IS NOT HANDICAP ACCESSIBLE",
                result_status = "FAVORABLE"
                # sponsors be the committe on council? have role but no seat?
            ),
            decision = "FAVORABLE",
            votes = [
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Andrea L. Boone",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 10",
                            roles = ingestion_models.Role("Chair"))
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Amir R Farokhi",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 2"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Dustin Hillis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 9"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Antonio Lewis",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 12"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Mary Norwood",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 8"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Howard Shook",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "District 7"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                ),
                ingestion_models.Vote(
                    # store in a dict?
                    person = ingestion_models.Person(
                        "Matt Westmoreland",
                        is_active = "true",
                        seat = ingestion_models.Seat(
                            "Post 2 At-Large"
                            # if role is notr mentioned should we assume member?
                        )
                    ),
                    decision = "AYES"
                )      
            ]
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("WALK-IN LEGISLATION")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("REQUESTED ITEMS")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("ADJOURNMENT")
        )
    ],
    agenda_uri = "https://atlantacityga.iqm2.com/Citizens/FileOpen.aspx?Type=14&ID=3175&Inline=True",
    minutes_uri = "https://atlantacityga.iqm2.com/Citizens/FileOpen.aspx?Type=12&ID=3370&Inline=True"
)

with open("example-cdp-event.json", "w") as open_f:
    open_f.write(event.to_json(indent=4))