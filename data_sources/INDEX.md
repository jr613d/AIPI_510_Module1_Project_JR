# Data Sources Index

Inventory of the data sources actually used directly in the project. Everything else explored during planning — dead ends, reference material, sources considered but not used — is captured in `RESEARCH_APPENDIX.md`.

**On the `.xlsx` files:** several DPI tables below were downloaded as `.xlsx` and converted to `.csv` with no other change. Only the `.csv` versions are committed to git — the `.xlsx` originals are gitignored to keep the repo from carrying two copies of the same numbers. All of them come from the same place, the NC DPI School Report Card researcher download: https://www.dpi.nc.gov/data-reports/school-report-cards/school-report-card-resources-researchers — so any conversion can be re-checked by re-downloading the bulk ZIP and pulling the table out again.

| File | What it is |
|---|---|
| `board_retreat_deck_2025-12-11.pdf` | CHCCS Board of Education retreat deck, Dec 11, 2025. Source of the financial-impact tables and the "Funding in Arrears" model. |
| `closure_study_2026-05-07.pdf` | CHCCS's "Study of the Proposed Closure of Ephesus, Glenwood and Seawell Elementary Schools," presented May 7, 2026. Source of per-school 10-year projections and the homeschool zone-of-residence tables. |
| `nc_dpi_rcd_adm_2024-25.csv` | NC DPI's official `rcd_adm` table (real historical Average Daily Membership by school and district, 2006-2025), converted from the source `.xlsx`. |
| `nc_dpi_report_card_data_dictionary_2024-25.xlsx` | NC DPI's official data dictionary for the School Report Card bulk data. Confirms the `rcd_adm` table's schema and CHCCS's LEA/agency code (681). Also available as four per-sheet CSVs (`..._general_rules.csv`, `..._table_index.csv`, `..._sy2425_columns.csv`, `..._code_definitions.csv`). |
| `nc_dpi_rcd_acc_eds_2024-25.csv` | NC DPI's `rcd_acc_eds` table — % Economically Disadvantaged Students by LEA, 2017-2025. Used in Section 6-8's cross-LEA comparison. |
| `nc_dpi_rcd_chronic_absent_2024-25.csv` | NC DPI's `rcd_chronic_absent` table — chronic absenteeism rate by LEA and subgroup, 2018-2025. Filtered to the "ALL" subgroup for the cross-LEA comparison. |
| `nc_dpi_rcd_funds2_2024-25.csv` | NC DPI's `rcd_funds2` table — per-pupil expenditure by LEA and spending category, 2019-2025. Filtered to the "TOTAL" category. |
| `nc_dpi_rcd_pk_enroll_2024-25.csv` | NC DPI's `rcd_pk_enroll` table — Pre-Kindergarten enrollment by LEA and subgroup, 2018-2025. Filtered to the "ALL" subgroup. |
| `nc_dpi_rcd_location_2024-25.csv` | NC DPI's `rcd_location` table — one row per school per year with its name, grade span (`PK:05`, `09:12`, etc.) and grade-span category (`E`/`M`/`H`/`A`/`I`/`T`). This is what makes elementary-only enrollment possible: DPI publishes no grade-level enrollment table, so elementary ADM has to be built by summing school-level ADM for schools this table marks as elementary. |
| `census_saipe_nc_school_districts_2019.txt` through `..._2024.txt` | Census SAIPE school-district population estimates for NC — total population and population ages 5-17, one file per year, 2019-2024. Fixed-width text, as published. Used in Section 5's enrollment-vs-population comparison. |
| `nces_ccd_lea_directory_nc_2022.json` | NCES Common Core of Data district directory for NC. Used only as a crosswalk — it lists each district's federal NCES ID alongside DPI's own agency code, which is what lets the SAIPE files above be matched to our DPI data. See `src/build_lea_population_crosswalk.py`. |
