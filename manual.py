from cdp_backend.pipeline import ingestion_models
from datetime import datetime

event = ingestion_models.EventIngestionModel(
    body=ingestion_models.Body("CITY OF HOUSTON . CITY COUNCIL", is_active=True),
    sessions=[
        ingestion_models.Session(
            # session 0 no video, combine with session 1?????????????
            video_uri="https://houstontx.new.swagit.com/videos/176697/embed",
            session_index=1,
            session_datetime='June 15, 2022'
        )
    ],
    event_minutes_items = [
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("PRESENTATIONS")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("ROLL CALL AND ADOPT THE MINUTES OF THE PREVIOUS MEETING")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("MAYOR'S REPORT")
        ),
        # where should i put ACCEPT WORK???? following two belongs to accept work but not matters
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("RECOMMENDATION from Director Houston Public Works for approval of final contract amount of $2,949,927.38 and acceptance of work on contract with REYTEC CONSTRUCTION RESOURCES, INC for FY2018 Drainage Rehab Work Orders #4 - 1.67% under the original Contract Amount - DISTRICTS A - PECK; B - JACKSON; C - KAMIN; D - EVANS-SHABAZZ; E - MARTIN; G - HUFFMAN; H - CISNEROS; I - GALLEGOS and K - CASTEX-TATUM")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("RECOMMENDATION from Director Houston Public Works for approval of final contract amount of $2,979,476.73 and acceptance of work on contract with GRAVA LLC for FY2019 Open Drainage System Maintenance Work Orders #1 - 0.68% under the original Contract Amount - DISTRICTS A - PECK; B - JACKSON; C - KAMIN; D - EVANS-SHABAZZ; E - MARTIN; G - HUFFMAN; H - CISNEROS; I - GALLEGOS; J - POLLARD and K - CASTEX-TATUM")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("PROPERTY - NUMBER 3")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("PURCHASING and TABULATION OF BIDS - NUMBERS 4 through 9")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("ORDINANCES - NUMBERS 10 through 26"),
            matter = #How to add more matters
                ingestion_models.Matter(
                "ORDINANCE approving and authorizing third amendment to contract between City of Houston and BRENTWOOD ECONOMIC COMMUNITY DEVELOPMENT CORPORATION, d/b/a BRENTWOOD COMMUNITY FOUNDATION, to extend term of contract and provide additional Housing Opportunities for Persons With AIDS Funds for the continuing administration and operation of a Community Residence and an Emergency Rental Assistance Program with Supportive Services - $892,634.00 - Grant Fund - DISTRICT K - CASTEX-TATUM", 
                matter_type = "ORDINANCES - NUMBERS 10 through 26",
                # title??
                title = "ORDINANCE approving and authorizing Subrecipient Agreement between City of Houston and CATHOLIC CHARITIES OF THE ARCHDIOCESE OF GALVESTON-HOUSTON to provide Emergency Solutions Grant (ESG), and Emergency Solutions Grant Coronavirus (ESG-CV) Funds for administration and related services in connection with the City’s Emergency Rental Assistance Program, for households that have been affected by COVID-19 - $3,058,423.79 - Grant Fund"
                ),
            decision = "ADOPTED",
            votes = [
            ingestion_models.Vote(
                person = ingestion_models.Person(
                    "Amy Peck",
                    is_active = "true",
                    # only has seat/role, what to do when only has role??
                    seat = ingestion_models.Seat(
                        "District A"
                    )
                ),
                decision = "AYES"
            ),
            ingestion_models.Vote(
                person = ingestion_models.Person(
                    "Mike Knox",
                    is_active = "true",
                    seat = ingestion_models.Seat(
                        "Position 1"
                    )
                ),
                decision = "AYES"
            )
            ]
            # no decision and votes info, can only find pdf
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("NON-CONSENT - MISCELLANEOUS")
        ),
        ingestion_models.EventMinutesItem(
            minutes_item = ingestion_models.MinutesItem("MATTERS HELD - NUMBERS 28 and 29")
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
        )
    ],
    agenda_uri = "https://houston.novusagenda.com/agendapublic//MeetingView.aspx?doctype=Agenda&MinutesMeetingID=0&meetingid=544",
    minutes_uri = "https://houston.novusagenda.com/agendapublic//MeetingView.aspx?doctype=Agenda&MinutesMeetingID=0&meetingid=544"
)

with open("example-cdp-event.json", "w") as open_f:
    open_f.write(event.to_json(indent=4))