# NIGAA Web Application Master Document

---

## 1. Title Page

| | |
|---|---|
| **Application Name** | NIGAA — Petition Tracker |
| **Department / Organization** | APTRANSCO — Vigilance & Security Wing |
| **Version** | 1.0 |
| **Date** | March 23, 2026 |
| **Prepared By** | Vigilance & Security IT Team, APTRANSCO |

---

## 2. Overview

### What the Application Does

NIGAA is a web-based vigilance petition tracking and workflow management application. It enables APTRANSCO and associated DISCOM offices (APSPDCL, APEPDCL, APCPDCL) to register, route, investigate, review, and close vigilance petitions through a centralized digital platform.

### Who Uses It

- **JMD Office** (Joint Managing Director — Vigilance & Security)
- **Personal Officer (Vigilance)** — PO
- **Chief Vigilance Officers (CVO)** — APSPDCL (Tirupathi), APEPDCL (Vizag), APCPDCL (Vijayawada)
- **DSP — Headquarters**
- **Field Inspectors** — CI (Circle Inspector) and SI (Sub Inspector)
- **CMD** — APSPDCL, APEPDCL, APCPDCL
- **CGM/HR TRANSCO**
- **Data Entry Operators**
- **Super Administrators**

### Why It Exists

Before NIGAA, vigilance petitions were tracked manually across multiple offices using spreadsheets, registers, and paper files. This led to delays, lost petitions, missed SLA deadlines, lack of visibility, and no audit trail. NIGAA digitizes the entire lifecycle — from petition receipt to investigation to closure — with role-based access, workflow enforcement, and real-time status tracking.

### Main Business Benefit

- Eliminates manual tracking and reduces petition processing time
- Provides full audit trail and accountability at every workflow stage
- Enforces SLA monitoring with dashboards and alerts
- Standardizes petition handling across all APTRANSCO and DISCOM offices
- Enables role-based access control ensuring data security and segregation of duties

---

## 3. User Roles

### 3.1 Super Admin

| | |
|---|---|
| **Purpose** | Full system administration and oversight |
| **Can Access** | All modules: Dashboard, SLA Dashboard, Petitions, New Petition, Petition Details, User Management, Form Management, Bulk Petition Upload, My Profile, Help Center Management, Notifications |
| **Can Do** | Create/manage users, approve/reject password recovery requests, bulk upload users, configure form fields and labels, create and track petitions, perform any workflow action, import historical petitions via Bulk Petition Upload or Help & Resources tab |
| **Cannot Access** | N/A — has unrestricted access |

### 3.2 Data Entry Operator

| | |
|---|---|
| **Purpose** | Register new petitions and route them into the workflow |
| **Can Access** | Dashboard, Petitions List, New Petition, Petition Details (view only), My Profile, Notifications |
| **Can Do** | Create new petitions, enter petitioner details, attach e-receipt files, forward petitions to the appropriate CVO/DSP or PO route |
| **Cannot Access** | User Management, Form Management, SLA Dashboard, Bulk Petition Upload. Cannot perform workflow actions (approve, assign inspector, add comments, close) |

### 3.3 Personal Officer — Vigilance (PO)

| | |
|---|---|
| **Purpose** | Permission decisions, e-office file management, petition closure, and oversight |
| **Can Access** | Dashboard, SLA Dashboard, Petitions, Petition Details, Bulk Petition Upload, My Profile, Notifications |
| **Can Do** | Approve or reject permission requests, assign e-office file numbers, forward petitions to CVO/DSP, give conclusions and close petitions, instruct CMD action, forward to JMD, import historical petitions via Bulk Petition Upload or Help & Resources tab |
| **Cannot Access** | User Management, Form Management, New Petition creation |

### 3.4 CVO / DSP (Chief Vigilance Officer / Deputy Superintendent of Police)

Roles: `CVO APSPDCL`, `CVO APEPDCL`, `CVO APCPDCL`, `DSP Headquarters`

| | |
|---|---|
| **Purpose** | Route petitions, assign field inspectors, review enquiry reports, and add comments |
| **Can Access** | Dashboard, SLA Dashboard, Petitions (within their office scope), Petition Details, My Profile, Notifications |
| **Can Do** | Set e-receipt numbers, upload e-receipt files, decide direct or permission-based enquiry, assign petitions to field inspectors, upload memos, review inspector reports, add CVO comments, upload consolidated reports, forward to JMD/PO, lodge media-source cases after report |
| **Cannot Access** | User Management, Form Management, Bulk Petition Upload, New Petition creation. Cannot see petitions outside their office jurisdiction |

### 3.5 Field Inspector (CI / SI)

| | |
|---|---|
| **Purpose** | Conduct field enquiries and submit investigation reports |
| **Can Access** | Dashboard (limited), Petitions assigned to them, Petition Details, My Profile, Notifications |
| **Can Do** | View assigned petitions, upload enquiry reports with PDF attachments, enter findings and recommendations, report electrical accident details, request conversion from preliminary to detailed enquiry |
| **Cannot Access** | User Management, Form Management, SLA Dashboard, New Petition, Bulk Petition Upload. Cannot access petitions assigned to other inspectors |

### 3.6 CMD (Commanding Officer)

Roles: `CMD APSPDCL`, `CMD APEPDCL`, `CMD APCPDCL`

| | |
|---|---|
| **Purpose** | Submit action taken reports when instructed by PO |
| **Can Access** | Dashboard (limited), Petitions sent for CMD action, Petition Details, My Profile, Notifications |
| **Can Do** | Submit action taken details, upload action report PDFs |
| **Cannot Access** | User Management, Form Management, SLA Dashboard, New Petition, Bulk Petition Upload. Limited to petitions within their organization scope |

### 3.7 CGM/HR TRANSCO

| | |
|---|---|
| **Purpose** | Submit action taken reports for headquarters-scope workflows |
| **Can Access** | Dashboard (limited), Petitions sent for action, Petition Details, My Profile, Notifications |
| **Can Do** | Submit action taken details, upload action report PDFs |
| **Cannot Access** | User Management, Form Management, SLA Dashboard, New Petition, Bulk Petition Upload |

---

## 4. Modules

### 4.1 Dashboard

| | |
|---|---|
| **Purpose** | Provides a role-based operational overview of petition activity with KPIs, charts, and filters |
| **Inputs** | Date range, petition type, source, office, target CVO, officer filters |
| **Outputs** | KPI cards (total, open, closed, pending), analytics charts (trends, sources, types, SLA), recent petitions list |
| **Screenshot** | `[Dashboard with KPI cards, charts, sidebar, and filter panel]` |

**Steps to Use:**
1. Click **Dashboard** in the sidebar
2. Set filters (date range, petition type, source, office)
3. Click **Apply**
4. Review KPI cards and analytics charts
5. Click any KPI card or chart segment to drill down into details
6. Click a recent petition to open its detail page

---

### 4.2 SLA Dashboard

| | |
|---|---|
| **Purpose** | Track SLA compliance — open, closed, within-SLA, and beyond-SLA petitions by employee and workload |
| **Inputs** | None (auto-loads current data) |
| **Outputs** | KPI tiles (total, open, closed, within SLA, beyond SLA), employee load charts, compliance/violation charts, employee SLA profiles |
| **Screenshot** | `[SLA Dashboard with KPI tiles, employee grid, and compliance charts]` |

**Steps to Use:**
1. Click **SLA Dashboard** in the sidebar
2. Review KPI tiles for SLA overview
3. Click any KPI tile to see related petitions
4. Click an employee name to open their individual SLA profile page

---

### 4.3 Petitions List

| | |
|---|---|
| **Purpose** | Browse and filter all petitions visible to the current user based on role and office scope |
| **Inputs** | Mode selector (All / Direct / Permission Based), status filter |
| **Outputs** | Paginated petition table with S.No, petitioner name, subject, type, status, date |
| **Screenshot** | `[Petitions list with mode pills, status filter, and petition table]` |

**Steps to Use:**
1. Click **Petitions** in the sidebar
2. Select mode: **All**, **Direct**, or **Permission Based**
3. Use the status filter dropdown to narrow results
4. Click **View** on any row to open petition details

---

### 4.4 New Petition (Data Entry)

| | |
|---|---|
| **Purpose** | Register a new vigilance petition into the system |
| **Inputs** | Received date, office, e-receipt number/file, target CVO/DSP, permission request type, petitioner details (name, contact, place), subject, petition type, source, government institution type, remarks |
| **Outputs** | Auto-generated petition S.No (format: `VIG/JMD/2025/0001`), automatic workflow routing |
| **Screenshot** | `[New petition form with all fields and Save Petition button]` |

**Steps to Use:**
1. Click **New Petition** in the sidebar
2. Enter **Received Date** and select **Received At** office
3. Enter **E-Receipt No** and upload **E-Receipt File** (PDF) if applicable
4. Select **Target CVO/DSP** and **Permission Request** type
5. Choose petitioner identity (Identified / Anonymous)
6. If identified: enter petitioner name, contact number, and place
7. Enter **Subject**, select **Type of Petition** and **Source of Petition**
8. If source is **Govt**: select **Government Institution Type**
9. Add remarks if needed
10. Click **Save Petition**

---

### 4.5 Petition Details (Workflow Page)

| | |
|---|---|
| **Purpose** | Central workflow page for viewing petition data, current status, enquiry reports, attachments, and performing role-based actions |
| **Inputs** | Role-specific actions (approve, reject, assign inspector, upload report, add comments, give conclusion, close) |
| **Outputs** | Petition information card, workflow stage tracker, status badges, enquiry report sections, tracking history timeline |
| **Screenshot** | `[Petition details with stage tracker, information card, action panel, and tracking history]` |

**Steps to Use:**
1. Open a petition from the Dashboard or Petitions list
2. Review the petition information card
3. Review the workflow stage tracker showing current status
4. Perform the next available action based on your role
5. Review tracking history at the bottom of the page

---

### 4.6 User Management

| | |
|---|---|
| **Purpose** | Admin-only module for creating and managing user accounts, password recovery approvals, and inspector-to-CVO mappings |
| **Inputs** | Username, password, officer name, role, CVO office mapping, phone, email, profile photo |
| **Outputs** | Created/updated user accounts, approved/rejected password recovery requests |
| **Screenshot** | `[User management with create officer form, password recovery queue, and officer directory]` |

**Steps to Use:**
1. Click **User Management** in the sidebar (Super Admin only)
2. **Create a user:** Fill username, password, officer name, role, and CVO mapping → Click **Create User**
3. **Bulk create users:** Upload Excel/CSV file with user data
4. **Manage existing user:** Select from dropdown → Expand **Manage User** → Update details
5. **Password recovery:** Review pending requests → Approve or Reject

---

### 4.7 Form Management

| | |
|---|---|
| **Purpose** | Admin-only module to configure dynamic form labels, field types, required rules, and dropdown options |
| **Inputs** | Form group, field selection, label text, field type, required flag, dropdown options |
| **Outputs** | Updated form configuration applied across the application |
| **Screenshot** | `[Form management with field editor, label, type, required toggle, and dropdown options]` |

**Steps to Use:**
1. Click **Form Management** in the sidebar (Super Admin only)
2. Choose a form group and field
3. Update the label, field type, or required rule
4. Edit dropdown options if applicable
5. Click **Save Field**

---

### 4.8 Bulk Petition Import

| | |
|---|---|
| **Purpose** | Import historical/legacy petitions using a standardized template |
| **Inputs** | `.xlsx` or `.csv` file following the system template |
| **Outputs** | Imported petition records with system-generated S.No values |
| **Access** | PO and Super Admin — via **Bulk Petition Upload** sidebar link or via the **Help & Resources** tab |
| **Screenshot** | `[Bulk petition import with template download, file upload, and field mapping rules]` |

**Access Path 1 — Sidebar (Dedicated Page):**
1. Click **Bulk Petition Upload** in the sidebar (PO / Super Admin)
2. Click **Download Template** to get the standard `.csv` format
3. Fill in historical petition data in the template
4. Upload the completed `.xlsx` or `.csv` file
5. Review flash messages for import results (success count, warnings, errors)

**Access Path 2 — Help & Resources Tab:**
1. Click **Help & Resources** in the sidebar
2. Scroll to the **Bulk Upload Previous Petitions** card (visible only to PO / Super Admin)
3. Click **Download Template (.csv)** to get the standard format
4. Fill in historical petition data — only the `subject` column is required; all other fields auto-fill with defaults if missing
5. Upload the completed `.xlsx` or `.csv` file and click **Upload & Import**
6. Expand **View Field Mapping Reference** to see the full column-to-field mapping table and accepted aliases
7. Review flash messages for import results (success count, warnings, errors)

**Field Mapping Behavior:**
- Only `subject` is mandatory — all other columns are optional
- Missing `received_date` defaults to today's date
- Missing `petitioner_name` defaults to "Anonymous"
- Missing `petition_type` defaults to "Other"
- Missing `source_of_petition` defaults to "Public Individual"
- `received_at` and `target_cvo` are auto-derived from each other when one is provided
- `permission_request_type`, `requires_permission`, and `permission_status` are auto-resolved when partial data is provided
- Invalid `status` values are mapped to "Received"
- Column headers support aliases (e.g., "date" → `received_date`, "petitioner" → `petitioner_name`, "type" → `petition_type`)
- `assigned_inspector_username` maps the petition to a field inspector if a valid username is found in the system

---

### 4.9 My Profile

| | |
|---|---|
| **Purpose** | Self-service profile management for all users |
| **Inputs** | Full name, username, new password, phone, email, profile photo |
| **Outputs** | Updated user profile |
| **Screenshot** | `[My Profile screen with name, username, password fields, photo upload, and Save Profile]` |

**Steps to Use:**
1. Click **My Profile** in the sidebar
2. Update full name, phone, email, or password as needed
3. Upload or remove profile photo
4. Click **Save Profile**

---

### 4.10 Notifications

| | |
|---|---|
| **Purpose** | Alert users about pending petitions and actions requiring attention |
| **Inputs** | Automatic — generated by petition workflow events |
| **Outputs** | Bell icon with count badge, dropdown list with petition links |
| **Screenshot** | `[Top bar notification bell with count badge and dropdown menu]` |

**Steps to Use:**
1. Click the **bell icon** in the top bar
2. Review pending notification items
3. Click any notification to navigate to the relevant petition

---

### 4.11 Help Center

| | |
|---|---|
| **Purpose** | Provide users with guides, documents, video resources, and bulk petition import capability |
| **Inputs** | Admin uploads help resources (documents, videos, external links); PO/Super Admin can upload petition import files |
| **Outputs** | Browsable help resource library; imported petition records (via bulk upload) |
| **Screenshot** | `[Help center with resource cards, bulk upload section, and admin management panel]` |

**Steps to Use (All Users):**
1. Click **Help & Resources** in the sidebar
2. Browse available guides, documents, and videos by category (User Manuals, Flowcharts, Videos, Office Orders, News)
3. Click any resource to view, preview inline, or download

**Steps to Use (PO / Super Admin — Bulk Upload):**
1. Click **Help & Resources** in the sidebar
2. Scroll to the **Bulk Upload Previous Petitions** card
3. Download the template, fill in petition data, and upload — see Section 4.8 for detailed field mapping
4. Flash messages confirm import results (success count, warnings, errors)

**Steps to Use (PO / Super Admin — Resource Management):**
1. Scroll to **Add Help Resource** section
2. Enter title, category, and upload file or paste external URL
3. Click **Upload & Save**
4. Manage visibility (show/hide) in the **Manage Resources** section below

---

### 4.12 Settings & Language

| | |
|---|---|
| **Purpose** | Theme toggle (dark/light mode) and language switching (English / Telugu) |
| **Inputs** | Toggle switches in the top bar |
| **Outputs** | Updated UI theme and language |
| **Screenshot** | `[Top bar showing theme toggle, language switch, and date display]` |

**Steps to Use:**
1. Click the **theme toggle** in the top bar to switch between dark and light mode
2. Click the **language toggle** to switch between English and Telugu

---

## 5. Main Workflows

### Workflow 1: Create and Submit a New Petition

| Step | Action | Role |
|------|--------|------|
| 1 | Log in with credentials + CAPTCHA | Any authorized user |
| 2 | Open **New Petition** from sidebar | Data Entry / Super Admin |
| 3 | Enter received date, office, e-receipt details | Data Entry |
| 4 | Select target CVO/DSP and permission request type | Data Entry |
| 5 | Enter petitioner details (or mark as anonymous) | Data Entry |
| 6 | Fill subject, petition type, source, and remarks | Data Entry |
| 7 | Click **Save Petition** | Data Entry |
| 8 | System generates S.No and routes automatically | System |

---

### Workflow 2: Permission-Based Petition Routing

| Step | Action | Role |
|------|--------|------|
| 1 | Petition is created with **Permission Required** | Data Entry |
| 2 | Petition appears in PO's queue with "Sent for Permission" status | System |
| 3 | PO reviews the petition and supporting documents | PO |
| 4 | PO selects target CVO/DSP, enters E-Office File No | PO |
| 5 | PO **Approves** (routes to CVO) or **Rejects** (petition marked rejected) | PO |
| 6 | If approved: petition moves to the target CVO/DSP | System |

---

### Workflow 3: Direct Enquiry Routing

| Step | Action | Role |
|------|--------|------|
| 1 | Petition is created with **Direct Enquiry** type | Data Entry |
| 2 | Petition is forwarded directly to the target CVO/DSP | System |
| 3 | CVO sets **E-Receipt Number** and uploads E-Receipt copy | CVO/DSP |
| 4 | CVO assigns petition to a **Field Inspector** (CI/SI) | CVO/DSP |
| 5 | CVO uploads memo/instructions PDF if needed | CVO/DSP |

---

### Workflow 4: Field Investigation and Report Submission

| Step | Action | Role |
|------|--------|------|
| 1 | Inspector opens the assigned petition | Inspector |
| 2 | Inspector conducts field enquiry | Inspector |
| 3 | Inspector enters conclusion, recommendations | Inspector |
| 4 | Inspector uploads **Enquiry Report PDF** | Inspector |
| 5 | For **Electrical Accident** type: enters accident category details | Inspector |
| 6 | For **Preliminary** enquiry: selects next step (send report to CVO / request conversion to detailed) | Inspector |
| 7 | Click **Upload Report** | Inspector |

---

### Workflow 5: CVO Review and Forwarding

| Step | Action | Role |
|------|--------|------|
| 1 | CVO opens petition after inspector report submission | CVO/DSP |
| 2 | Reviews the uploaded report and recommendations | CVO/DSP |
| 3 | Enters **CVO Comments** | CVO/DSP |
| 4 | Uploads **Consolidated Report File** if needed | CVO/DSP |
| 5 | Forwards petition to **JMD** or **PO** | CVO/DSP |
| 6 | For media-source cases: CVO can directly **Lodge** the petition | CVO/DSP |

---

### Workflow 6: PO Conclusion and Closure

| Step | Action | Role |
|------|--------|------|
| 1 | PO opens petition forwarded from CVO/JMD | PO |
| 2 | Reviews all reports, comments, and attachments | PO |
| 3 | Enters **E-Office File No** | PO |
| 4 | Gives **Conclusion** and uploads conclusion file | PO |
| 5 | Either **Closes** the petition or instructs **CMD Action** | PO |

---

### Workflow 7: CMD/CGM Action Report

| Step | Action | Role |
|------|--------|------|
| 1 | CMD/CGM opens petition in "Sent to CMD for Action" status | CMD / CGM/HR |
| 2 | Enters **Action Taken** details | CMD / CGM/HR |
| 3 | Uploads **Action Report PDF** | CMD / CGM/HR |
| 4 | Submits the action report | CMD / CGM/HR |
| 5 | Petition returns to PO for final closure | System |

---

## 6. Reports

### Available Reports / Analytics

| Report / View | Description | Access |
|---|---|---|
| **Dashboard KPI Cards** | Total, open, closed, pending petitions with clickable drill-down | All roles (scope-filtered) |
| **Petition Trend Charts** | Monthly/yearly petition volume trends | Dashboard |
| **Source Distribution** | Breakdown by petition source (Media, Public, Govt, Sumoto, CMD) | Dashboard |
| **Type Distribution** | Breakdown by petition type (Bribe, Corruption, Harassment, etc.) | Dashboard |
| **SLA Compliance Report** | Within-SLA vs Beyond-SLA metrics | SLA Dashboard |
| **Employee Workload Report** | Petition load per officer with SLA status | SLA Dashboard |
| **Employee SLA Profile** | Individual officer's petition handling performance | SLA Dashboard |
| **Tracking History** | Chronological audit trail of every action on a petition | Petition Details |
| **Analysis Report** | Detailed analytics and cross-tabulation view | Analysis Report page |

### Filters

- **Date range** (from / to)
- **Petition type** (Bribe, Corruption, Harassment, Electrical Accident, Misconduct, Works Related, Irregularities in Tenders, Illegal Assets, Fake Certificates, Theft/Misappropriation, Other)
- **Source of petition** (Electronic & Print Media, Public, Govt, Sumoto, O/o CMD)
- **Receiving office** (JMD Office, CVO APSPDCL, CVO APEPDCL, CVO APCPDCL)
- **Target CVO/DSP**
- **Officer / Employee**
- **Status**

### Export Options

- Dashboard and SLA dashboard data are viewable on-screen with drill-down
- Petition tracking history is viewable in-page
- PDF file attachments (e-receipts, memos, enquiry reports, action reports, conclusion files) are downloadable

### Who Can Access Reports

| Report | Roles with Access |
|---|---|
| Dashboard | All authenticated users (filtered by role/office scope) |
| SLA Dashboard | Super Admin, PO, CVO/DSP |
| Petition Details & Tracking History | All users with access to the specific petition |
| Analysis Report | Super Admin, PO |

---

## 7. FAQ / Troubleshooting

### Forgot Password

**Solution:**
1. On the login page, click **Forgot Password**
2. Enter your username and your desired new password
3. Continue to password reset after username validation
4. If recovery is not available, the request is sent to the Super Admin for approval
5. Wait for admin to approve the password reset request
6. Once approved, log in with your new password

---

### Invalid Login / Cannot Log In

**Possible Causes & Solutions:**

| Cause | Solution |
|---|---|
| Wrong username or password | Re-enter correct credentials |
| CAPTCHA answer incorrect | Solve the displayed sum accurately |
| Recovery not available | Check your username details or contact admin |
| Recovery session expired | Return to login page and restart the process |
| Account deactivated | Contact Super Admin to reactivate your account |
| Account locked after repeated failures | Wait for lockout expiry or contact admin |

---

### Missing Data / Petition Not Visible

**Possible Causes & Solutions:**

| Cause | Solution |
|---|---|
| Petition is outside your role/office scope | You can only see petitions assigned to your role and jurisdiction |
| Status filter is active | Clear or change the status filter on the Petitions page |
| Wrong mode selected | Switch between **All**, **Direct**, and **Permission Based** modes |
| Petition not yet routed | Check with Data Entry if the petition has been created and forwarded |

---

### Report Not Loading / Charts Not Displaying

**Possible Causes & Solutions:**

| Cause | Solution |
|---|---|
| No data in selected date range | Expand the date range filter |
| Browser compatibility issue | Use a modern browser (Chrome, Edge, Firefox) |
| Network connectivity issue | Check your internet/network connection |
| Browser cache issue | Clear browser cache or do a hard refresh (Ctrl+Shift+R) |

---

### Permission Denied / Cannot Perform Action

**Possible Causes & Solutions:**

| Cause | Solution |
|---|---|
| Role does not have permission | Only specific roles can perform specific actions (see Section 3) |
| Petition is not at the right workflow stage | Wait for the petition to reach the correct status for your action |
| PO approval pending | For permission-based cases, wait for PO to approve before proceeding |
| "Only PO can approve permission" error | Log in with the PO account to perform this action |

---

### File Upload Issues

**Possible Causes & Solutions:**

| Cause | Solution |
|---|---|
| File is not PDF | Convert to PDF before uploading |
| File exceeds 10 MB | Compress the file to under 10 MB |
| E-Receipt No entered without file | Upload the matching PDF file |
| E-Receipt file uploaded without number | Enter the E-Receipt number first |

---

### First-Time Login Issues

**Possible Causes & Solutions:**

| Cause | Solution |
|---|---|
| Forced password change prompt | All new accounts require a mandatory password change on first login. Enter your new password and registered phone number |
| Default password not working | The default password is set by the admin. Contact Super Admin to confirm |
| Phone number missing for recovery | Contact Super Admin to update your phone number in the system |

---

## 8. Benefits / Outcomes

### Time Saved

- **Before NIGAA:** Petitions were tracked manually through registers, Excel sheets, and paper files across multiple offices. Routing took days via physical dispatch.
- **After NIGAA:** Petitions are routed instantly to the correct CVO/DSP with automatic status updates. Average routing time reduced from days to minutes.

### Accuracy

- **Before:** Manual data entry across multiple registers led to duplicate entries, missing fields, and inconsistent records.
- **After:** Centralized digital entry with validation rules ensures every petition has complete, accurate data. CSRF protection and input validation prevent data integrity issues.

### Standardization

- **Before:** Each office followed its own tracking format and naming conventions.
- **After:** Unified petition numbering (VIG/JMD/YYYY/NNNN), standardized petition types, sources, and workflow stages across all APTRANSCO and DISCOM offices.

### Better Visibility

- **Before:** No real-time visibility into petition status. Supervisors relied on periodic manual reports.
- **After:** Real-time dashboards with KPIs, SLA monitoring, employee workload tracking, and drill-down analytics. Every action is logged in the tracking history for complete audit trail.

### Accountability

- **Before:** Difficult to track who handled a petition and when.
- **After:** Every workflow action is time-stamped and attributed to a specific user. SLA dashboards highlight overdue cases and employee-level performance.

### Security & Compliance

- **Before:** Paper-based records vulnerable to loss, unauthorized access, and tampering.
- **After:** Role-based access control, CAPTCHA-protected login, CSRF protection, session-based security, and structured security event logging.

---

## Appendix A: Tech Stack

| Component | Technology |
|---|---|
| Backend | Python Flask |
| Database | PostgreSQL 13+ |
| Frontend | HTML5, CSS3, JavaScript |
| Authentication | Session-based with Werkzeug password hashing |
| Password Recovery | Username-based reset workflow |
| Internationalization | English and Telugu (i18n) |
| Deployment | Waitress WSGI server, reverse proxy recommended |
| Security CI | GitHub Actions (lint, tests, pip-audit, dependency check) |

---

## Appendix B: Petition Fields Reference

| Field | Description | Required |
|---|---|---|
| S.No | Auto-generated (VIG/JMD/YYYY/NNNN) | Auto |
| Received Date | Date petition was received | Yes |
| Received At | Office where petition was received (JMD Office, CVO offices) | Yes |
| E-Receipt No | Receipt reference number | Conditional |
| E-Receipt File | PDF copy of e-receipt | Conditional |
| Target CVO/DSP | Destination vigilance office | Conditional |
| Permission Request | Direct or permission-based routing | Conditional |
| Petitioner Name | Name of petitioner | Conditional |
| Contact Number | Phone number | Conditional |
| Place | Location or area | Conditional |
| Subject | Petition subject or summary | Yes |
| Type of Petition | Bribe, Corruption, Harassment, Electrical Accident, Misconduct, Works Related, Irregularities in Tenders, Illegal Assets, Fake Certificates, Theft/Misappropriation, Other | Yes |
| Source of Petition | Electronic & Print Media, Public, Govt, Sumoto, O/o CMD | Yes |
| Govt Institution Type | Category for government source petitions | Conditional |
| Enquiry Type | Detailed or Preliminary | Yes |
| Remarks | Additional notes | Configurable |
| E-Office File No | Official file number (entered by PO) | At closure |
| Organization | APSPDCL / APEPDCL / APCPDCL / Headquarters | Conditional |

---

## Appendix C: Petition Status Values

| Status | Description |
|---|---|
| Received | Petition has been registered in the system |
| Forwarded to CVO | Routed to the target CVO/DSP office |
| Sent for Permission | Awaiting PO approval for permission-based enquiry |
| Permission Approved | PO has approved the enquiry |
| Permission Rejected | PO has rejected the permission request |
| Assigned to Inspector | CVO/DSP has assigned a field inspector |
| Enquiry in Progress | Field investigation is underway |
| Enquiry Report Submitted | Inspector has uploaded the enquiry report |
| CVO Comments Added | CVO has reviewed and commented on the report |
| Forwarded to JMD | Sent to JMD for review |
| Forwarded to PO | Sent to PO for conclusion |
| Conclusion Given | PO has provided a conclusion |
| Action Instructed | CMD/CGM action has been requested |
| Action Taken | CMD/CGM has submitted action report |
| Sent Back for Re-enquiry | Petition returned for additional investigation |
| Lodged | Petition formally recorded and disposed |
| Closed | Petition workflow is complete |

---

## Appendix D: Glossary

| Term | Meaning |
|---|---|
| APTRANSCO | Andhra Pradesh Transmission Corporation |
| CVO | Chief Vigilance Officer |
| DSP | Deputy Superintendent of Police |
| PO | Personal Officer (Vigilance) |
| JMD | Joint Managing Director |
| CMD | Chairman and Managing Director |
| CGM/HR | Chief General Manager — Human Resources |
| CI | Circle Inspector |
| SI | Sub Inspector |
| DISCOM | Distribution Company (APSPDCL, APEPDCL, APCPDCL) |
| SLA | Service Level Agreement |
| E-Receipt | Electronic receipt reference number and scanned document |
| E-Office File No | Official file number for downstream office processing |
| CAPTCHA | Security verification challenge on login |
| CSRF | Cross-Site Request Forgery (security protection) |
| Direct Enquiry | Route where CVO/DSP proceeds without PO permission |
| Permission Based | Route where PO approval is required before enquiry |
| Lodged | Petition moved into formal recorded disposition |
| Closed | Petition workflow completed |

---

*Document generated from NIGAA Petition Tracker codebase analysis — Version 1.0*
