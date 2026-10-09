---
date: 2026-10-02
type: reference
status: active
tags: [research, requirements, refresh-interval, hanoi, flood-onset, us-062]
related: ["[[US-062-map-refresh-requirement-research|map-refresh-requirement-research]]", "[[map-refresh-requirement-research-plan]]", "[[BL-010-map-shows-forecast-not-now|map-shows-forecast-not-now]]", "[[five-minute-tile-freshness]]", "[[2026-10-02]]"]
last_updated: 2026-10-02
---

# How fast must a user react to the flood map: findings

Findings of the internet research for story `US-062` ([[US-062-map-refresh-requirement-research|map-refresh-requirement-research]]). The plan and its Revision 1 are in [[map-refresh-requirement-research-plan]]. The search ran on 2026-10-02, in English and Vietnamese. Every row below was opened and read, not taken from a search snippet. Times in Hanoi are UTC+7.

## The answer in short

1. **Usual case, a short convective burst.** About 30 minutes of heavy rain (roughly 35 to 62 mm at the Hanoi gauges on 2026-07-27) floods streets within minutes. Reported street depths were 20 to 60 cm, and 80 cm to 1 m in a low alley. The water recedes in about 30 minutes to 2 hours. The person has minutes, not tens of minutes.
2. **Extreme case, a multi-hour or multi-day storm.** On 2026-09-16 to 09-17 a night of rain (80 to 199 mm, 19:00 to 03:00) gave 30 to 50 cm at 06:00 and nearly 1 m at some points by 09:00. Cumulative rain over 14 to 17 September reached 473 to 600 mm. The flood builds over hours and recedes over hours. The person has hours.
3. **The 30-minute understanding.** The sources support "30 minutes of heavy rain is enough to flood streets". They do not give a "flood arrives 30 minutes after the rain starts" figure. In the Vietnamese reports, "30 minutes" is the length of the rain burst and the time the water takes to recede. The only onset statements are "after only a few minutes" (Hanoi) and "after about 15 minutes" (Ho Chi Minh City). So flooding can start inside the 30 minutes.
4. **No source gives a measured rate of rise in cm per minute for Hanoi.** The Hanoi modelling papers work in days and hours. This is the main gap.
5. **Does a 15-minute refresh meet it?** For the extreme case, yes. For the usual case, a burst can start and flood a street within one refresh interval, so no refresh of the map can show it before it starts. Only a rain forecast can. The research found published skill of 15 to 20 minutes for rain nowcasts of convective storms. So the refresh interval is not the weakest link. The rain forecast is (inference, see "What this means").

## Evidence table

Tier 1 is a peer-reviewed work. Tier 2 is a preprint or an agency page. Tier 3 is a news report. A number from a news report is a report, not a measurement.

| ID | What it says | Source | Tier | Language | How checked |
| -- | ------------ | ------ | ---- | -------- | ----------- |
| E1 | Hanoi Central Area, four scenarios: 2008 event 563.3 mm over 3 days, max depth 2.08 m. Max two-day event 560.4 mm, 2.93 m. 200-year return 622 mm, 2.99 m. Probable maximum 840 mm, 3.23 m. Validation on the 30 Oct to 1 Nov 2008 flood with 9 reference photos, R² 0.6. The paper does not say when the maximum depth occurs, and it treats each day's rain as a fixed intensity per hour. | [Flood inundation assessment for the Hanoi Central Area, Vietnam](https://www.nature.com/articles/s41598-018-30024-5), Sci Rep 2018 | 1 | English | Full text read through Europe PMC |
| E2 | Review of pluvial flash flood early warning systems: a Thai system sends data every 10 minutes, a Puerto Rico radar has a 3 minute resolution with lead times of 10, 20, and 30 minutes, and the Barcelona system sent an email 90 minutes before the flooding on 29 Oct 2013. The review does not state a rain-to-flood response time. | [Real-Time Early Warning System Design for Pluvial Flash Floods, A Review](https://doi.org/10.3390/s18072255), Sensors 2018 | 1 | English | Full text read through Europe PMC |
| E3 | Rainfall nowcast: an ideal rainfall input for hydrological models has 1 to 5 minute resolution. Lagrangian persistence holds up to 20 minutes, and for convective events a lead time of 15 minutes should be assumed. | [Rainfall nowcasting by combining radars, microwave links and rain gauges](https://arxiv.org/abs/1810.11811), Bianchi et al., arXiv 2018 | 2 | English | Abstract and introduction read |
| E4 | Hanoi's automated system in 2018: rain sensors at 22 positions, updating in real time. Flooding points: 16 monitored, updated once every 30 minutes. | [Hanoi online environment monitoring page](https://cem.gov.vn/thong-tin-hoat-dong/ha-noi-cung-cap-thong-tin-truc-tuyen-ve-chi-so-quan-trac-moi-truong-tu-dong), published 2018-12-28 | 2 | Vietnamese | Page read |
| E5 | 2026-07-27: rain of about 30 minutes around 11:00. "After only a few minutes" central streets began to flood. Depths: 20 to 30 cm on Nguyễn Thái Học, 80 cm to 1 m at the end of alley 42 Giang Văn Minh. No rainfall amounts. | [Dân trí, 2026-07-27](https://dantri.com.vn/thoi-su/mua-30-phut-o-ha-noi-nhieu-tuyen-pho-ngap-nuoc-co-diem-sau-1-met-20260727125728491.htm) | 3 | Vietnamese | Article read |
| E6 | Same event, 2026-07-27: rain about 30 minutes. Gauges: Ba Đình 61.9 mm, Hoàn Kiếm 42 and 34.6 mm, Tây Hồ 38.5 mm, Phú Thượng 35.5 mm. Thụy Khuê 20 to 40 cm and up to 50 to 60 cm. No onset time. | [Tuổi Trẻ, 2026-07-27](https://tuoitre.vn/mua-30-phut-mot-so-tuyen-duong-o-ha-noi-ngap-sau-khien-nhieu-xe-chet-may-100260727130145636.htm) | 3 | Vietnamese | Article read |
| E7 | 2026-07-09: rain of 40 to 80 mm in a short time, with high intensity. The deputy director of the Hanoi Department of Construction said it overloaded drainage, and the water took about 30 minutes to clear after the flood control system was started. The new drainage covers about 20 percent of the planned system. | [Tuổi Trẻ, 2026-07-10](https://tuoitre.vn/ha-noi-ly-giai-vi-sao-vua-mua-30-phut-duong-pho-da-ung-ngap-du-vua-xay-he-thong-chong-ngap-100260710181446297.htm) | 3 | Vietnamese | Article read. The headline says streets flooded "after 30 minutes of rain", and the body does not say when the flooding started. |
| E8 | 2026-09-14 to 09-17: cumulative rain 600.3 mm at Yên Sở, 598.6 mm at Hai Bà Trưng, 473.2 mm at Cầu Giấy, called a record. Flooding lasted 30 minutes to 2 hours, against 4 to 10 hours in 2025. Source of the numbers: the Hanoi Technical Infrastructure Management Center. No rise rate. | [Công luận, 2026-09-17](https://congluan.vn/nhieu-diem-ngap-lut-keo-dai-den-10-tieng-o-ha-noi-nay-kho-rao-sau-30-phut-post361029.html) | 3 | Vietnamese | Article read |
| E9 | 2026-09-16 19:00 to 09-17 03:00: 80 to 160 mm over the city, up to 199 mm at Từ Liêm (Hanoi Water Drainage Company). At 06:00, flooding points at 30 to 50 cm. At 09:00, 40 to 50 cm in the central-west districts and nearly 1 m at Cầu Cốc and Ngọa Long. By noon the rain had stopped and 25 locations were still flooded. | [VnExpress live report, 2026-09-17](https://vnexpress.net/ha-noi-nhieu-noi-mua-vuot-150-mm-5121155-tong-thuat.html) | 3 | Vietnamese | Report read |
| E10 | Ho Chi Minh City, 2026-09-23: several roads were flooded to half the height of motorcycle wheels "after about 15 minutes of rain". Forecast depths 10 to 20 cm on 71 roads, 30 to 50 cm and 40 to 80 cm on others. Water may take more than 30 minutes, or more than 60 minutes in tidal areas, to recede. This is not Hanoi. | [SGGP, 2026-09-23](https://en.sggp.org.vn/heavy-rain-floods-roads-across-ho-chi-minh-city-post129876.html) | 3 | English | Article read |
| E11 | Users on a Hanoi flood information gap, 2026-09-23. A ride-hailing driver: "something that tells us which roads are passable and which ones to avoid, instead of finding out only when we arrive." Associate Professor Lưu Đức Hải: "A static flood map provides information only when it is already too late. A dynamic map must help people decide whether to continue, stop, or take another route." The article says the "Rain and Flood Map" feature was removed from iHanoi within 14 days. | [VnExpress International, 2026-09-23](https://e.vnexpress.net/news/life/hanoians-struggle-to-navigate-flooded-streets-without-real-time-warnings-5123728.html) | 3 | English | Article read |
| E12 | iHanoi's "Rain and Flood Map": rainfall and flood depth "continuously updated in real time", from the HSDC automated network. The article gives no number of gauges or interval. | [VietnamNet, 2026-09-04](https://vietnamnet.vn/en/hanoi-adds-real-time-rain-and-flooding-updates-to-ihanoi-for-safer-travel-2551919.html) | 3 | English | Article read |

## Derived numbers

These are my calculations from the table, not findings. They need the assumptions stated.

- **Burst intensity.** E6 gives 34.6 to 61.9 mm in about 30 minutes, which is about 69 to 124 mm per hour as an hourly equivalent. Our test storm is 50 mm/h. So the usual real burst is more intense than the test storm for 30 minutes, and the test storm lasts for hours, so its cumulative rain is larger. The test storm is not a stand-in for either case.
- **Depth over a burst.** E5 reports 80 cm to 1 m at an alley after a burst of about 30 minutes. If the flooding started a few minutes after the rain, the average rise in that alley was at least about 3 cm per minute. This is a floor from one resident's report on one alley, not a rate measured at a gauge.
- **Extreme case.** E9: from 06:00 to 09:00 the reported depth rose from 30 to 50 cm to 40 to 50 cm, with some points near 1 m. That is about a few cm per hour at most points, and the news does not report a depth series.

## What this means (inference)

1. **Time to act, usual case.** Flooding can appear within minutes of the heavy rain (E5) and within about 15 minutes in a comparable Vietnamese city (E10). A tile that is 15 to 30 minutes old by the clock cannot show a burst that starts after its run. What it can show is a forecast that includes the burst. The research found a nowcast skill of 15 to 20 minutes for convective storms (E3). A map that refreshes every 15 minutes uses that skill window about fully. A 5-minute refresh would add little unless the rain input also updates every 5 minutes, for example from radar.
2. **Time to act, extreme case.** The flood builds and recedes over hours (E8, E9). A 15-minute refresh is more than enough.
3. **What users want.** The quote in E11 is about route choice before arrival and while moving. The time that matters is the trip time to the flooded spot, usually minutes. That points to showing the age of the map and the forecast, not to a faster refresh.
4. **Benchmark.** Hanoi's own flooding-point monitor updated every 30 minutes (E4, 2018). Our 15-minute tile is twice as fast. This benchmark is old.

## Limits of this research

- No measured rate of rise in cm per minute for Hanoi was found (item 4 of the short answer). The papers found use hourly or daily rain.
- News reports (tier 3) carry most of the Hanoi onset evidence. They are qualitative and sometimes a resident's own estimate.
- Only English and Vietnamese sources were searched, through a web search tool that returns up to 10 results per query.
- Leads not opened or not readable, so not used: the Sensors review on the MDPI site (403 error, read through Europe PMC instead), a Tiền Phong report on the 200 mm event (only the title came back), a Đọc Nhanh report on the 30-minute rain (HTTP 410), and a Frontiers 2022 paper on flash flood warning in the El Guamo basin (a tool summary said the warning delay is about 20 minutes and that 10 to 60 minute intervals suit urban floods, but I did not read the sentences myself).
- Search snippets, not read: an equation for flood expansion rate (0.17 to 0.902) and depths of 0.3 to 0.8 m for 31 October 2008 in a health study. They are leads for a second pass.

## Recommended decision for US-062

The user decides. The evidence supports this order:

1. **Keep the 15-minute refresh.** For the extreme case it is more than needed. For the usual case a faster map cannot beat a burst that starts after the run.
2. **Show the age of the map**, for example "12 min ago", next to the "As of" time. This costs almost nothing.
3. **Do not build a 5-minute pipeline now.** Revisit it if the rain input becomes radar or gauge data every 5 minutes. The cost is in [[five-minute-tile-freshness]] and `marie-curie/idea-24h-five-minute-preview-run.md`.
4. **Next research, if wanted:** find a measured depth series for a Hanoi street during a burst (a water level sensor or a time-lapse report), and check how well the rain forecast we use (Tomorrow.io) predicts a 30-minute burst. Both need data we do not have yet.

## Decision for US-062

On 2026-10-02 the user decided to keep the 15-minute refresh for now. The decision does not include the map-age label (item 2 above) or a 5-minute pipeline (item 3), and no story is opened for either. The recommendation to revisit a faster refresh, if the rain input becomes radar or gauge data every 5 minutes, stands as written.

## Status history

- **2026-10-02, active.** Written after the search. Twelve sources read, and the leads that failed or were only snippets are listed above.
- **2026-10-02, active.** The user decided to keep the 15-minute refresh for now. `US-062` is `Done`.
