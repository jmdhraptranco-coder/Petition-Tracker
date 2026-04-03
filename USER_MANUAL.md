# USER MANUAL

## 1. Table of Contents

1. Title Page
2. Introduction
3. System Overview
4. Getting Started
5. Navigation Guide
6. Module-by-Module Guide
7. Task-Based Instructions
8. Field Explanations
9. Error Handling
10. Troubleshooting
11. Frequently Asked Questions (FAQ)
12. Glossary
13. Support Information
14. Screenshot Capture Checklist
15. Suggested UI Documentation Improvements
16. Optional Training Guide

## 2. Required Screenshots List

1. Login page
2. Password reset screen
3. Password recovery request screen
4. Main dashboard with sidebar and top bar
5. Dashboard filters panel
6. Dashboard KPI cards and analytics charts
7. Petitions list screen
8. New petition entry form
9. Petition form with Government source fields expanded
10. Petition form with anonymous petitioner option selected
11. Petition details page with workflow stage tracker
12. Petition details page showing petition information section
13. Petition details page showing tracking history
14. CVO/DSP action area for routing or assigning inspector
15. PO permission approval screen
16. Inspector enquiry report upload screen
17. Petition details page showing uploaded enquiry report stages
18. CMD action report submission screen
19. SLA dashboard overview
20. SLA employee profile page
21. User management landing screen
22. Create officer login form
23. Bulk user upload screen
24. Password recovery approvals queue
25. Officer directory and user controls
26. My Profile screen
27. Bulk petition import screen
28. Form management screen
29. Notifications menu
30. Petitioner profile pop-up modal

## 3. Missing Information Questions

The codebase confirms most application behavior, but these business details are not explicit in the project files:

1. What document version should appear on the title page?
2. What organization name should be shown exactly on the title page?
3. Who is the document owner or approving authority?
4. What support email, phone number, or helpdesk channel should users contact?
5. What is the formal escalation path after first-line support?
6. What is the production system URL users should open?
7. What browsers and minimum versions are officially supported by your IT team?
8. Do you want the manual branded as `Nigaa`, `Petition Tracker`, or `Nigaa Petition Tracker`?

Until you provide those, this manual uses clearly marked placeholders where needed.

---

## 4. Full User Manual

## Title Page

**Project Name:** Nigaa Petition Tracker  
**Version:** `[Insert Version]`  
**Date:** March 9, 2026  
**Organization:** `[Insert Organization Name]`  
**Document Owner:** `[Insert Document Owner]`

---

## Introduction

### Purpose of the System

Nigaa Petition Tracker is a web-based vigilance workflow application used to register, route, review, investigate, and close petitions across APTRANSCO-related vigilance offices and associated CVO/DSP offices.

### Who Should Read This Manual

This manual is intended for:

- Data Entry Operators
- Personal Officer (Vigilance)
- CVO/DSP officers
- Field Inspectors (CI/SI)
- CMD and CGM/HR approvers
- Super Administrators

### Key Capabilities

- Secure login with CAPTCHA
- Role-based access to petitions and workflow actions
- Petition registration and tracking from receipt to closure
- Permission-based and direct enquiry routing
- Inspector report submission with PDF attachment
- CVO comments and consolidation
- PO approval, file number management, and closure handling
- CMD action reporting
- SLA monitoring and employee-wise performance visibility
- User administration and password recovery approvals
- Bulk import for historical petitions and user accounts

### Business Benefits

- Reduces manual petition tracking
- Improves accountability through role-based workflow steps
- Maintains a visible audit trail and tracking history
- Supports SLA monitoring for operational control
- Standardizes vigilance petition handling across offices

---

## System Overview

### Architecture Overview

Nigaa Petition Tracker is a browser-based web application. Users access it through a web browser over the organization network or approved deployment URL. The application stores petition records, user accounts, workflow history, uploaded PDF documents, and reporting data in a central PostgreSQL database and file storage location.

### Main Modules

- Dashboard
  Shows petition KPIs, filters, charts, recent petitions, and summary analytics.
- SLA Dashboard
  Tracks open, closed, within-SLA, and beyond-SLA petitions by employee and workload.
- Petitions
  Displays the petition list, status filtering, and record-level access.
- New Petition
  Allows Super Admin and Data Entry users to register new petitions.
- Petition Details
  Central workflow screen for viewing petition data, status stages, reports, and actions.
- User Management
  Allows Super Admin to create logins, bulk upload users, approve password recovery, and maintain users.
- Bulk Petition Import
  Allows PO users to import historical or legacy petition data using a template.
- My Profile
  Lets users update their own profile, password, contact details, and photo.
- Form Management
  Allows Super Admin to configure form labels, field types, required rules, and dropdown options.

### User Roles and Permissions

| Role | Primary Access |
|---|---|
| Super Admin | Full access to all modules, users, and workflow actions |
| Data Entry Operator | Create petitions and forward them to the appropriate CVO/DSP or PO route |
| Personal Officer (Vigilance) | Permission decisions, e-office file handling, closure workflow, direct petition review, historical import |
| CVO/DSP - APSPDCL / APEPDCL / APCPDCL | Decide enquiry mode, assign inspectors, review reports, add comments, route petitions |
| DSP - Headquarters | Similar routing and review authority for headquarters scope |
| Field Inspector (CI/SI) | Receive assigned petitions and upload enquiry reports |
| CMD - APSPDCL / APEPDCL / APCPDCL | Submit action taken reports when action is instructed |
| CGM/HR TRANSCO | Submit action taken reports in applicable headquarters workflows |

### High-Level Workflow

1. A petition is entered by Data Entry or created in the applicable office flow.
2. The system routes it to PO or to the appropriate CVO/DSP, depending on receipt source and routing rules.
3. CVO/DSP decides whether the petition follows direct enquiry or permission-based workflow.
4. If permission is required, PO approves or rejects it.
5. CVO/DSP assigns the petition to a Field Inspector.
6. The Inspector submits an enquiry report and PDF attachment.
7. CVO/DSP reviews the report and adds comments or next-step actions.
8. PO records decision details, e-office file number, closure remarks, or forwards for CMD action.
9. CMD or CGM/HR submits action taken details where applicable.
10. The petition is lodged or closed, and tracking history remains available.

---

## Getting Started

### System Requirements

- Device: Desktop or laptop recommended; responsive layout also supports mobile view
- Browser: Modern web browser such as Google Chrome, Microsoft Edge, or Mozilla Firefox
- Internet/Network: Access to the deployed application URL and the organization network if hosted internally
- File Uploads:
  - PDF documents for e-receipts, memos, enquiry reports, and action reports
  - Maximum configured upload size: 10 MB per file

### Accessing the System

1. Open your approved system URL: `[Insert Production URL]`
2. The login page appears.
3. Enter your username and password.
4. Solve the CAPTCHA security check.

### Login Instructions

1. In the `Username` field, enter your assigned login ID.
2. In the `Password` field, enter your password.
3. In `Security Verification`, solve the displayed sum.
4. Click `Verify & Sign In`.

[Screenshot: Login Page]  
Highlight:
- Username field
- Password field
- CAPTCHA box
- Verify & Sign In button

Caption:
Enter your credentials, solve the CAPTCHA, and sign in.

### First-Time Setup

For first-time users:

1. Confirm your username and initial password with the system administrator.
2. Ensure your registered phone number is correct for recovery.
3. Sign in and open `My Profile`.
4. Update your password, phone number, email address, and profile photo if needed.

[Screenshot: My Profile Screen]  
Highlight:
- Full Name
- Username
- New Password
- Confirm New Password
- Save Profile

Caption:
Update profile information after first login.

---

## Navigation Guide

### Main Layout

After login, the system displays:

- Left sidebar for module navigation
- Top bar for page title, notifications, profile menu, language toggle, date, and theme toggle
- Main content area for the selected module

### Sidebar Menu

The visible menu depends on role. Common menu items include:

- Dashboard
- SLA Dashboard
- Petitions
- My Profile
- New Petition
- User Management
- Form Management
- Bulk Petition Upload
- Direct Petitions

### Top Bar Elements

- Notifications bell for pending petitions
- Profile menu for quick access to profile and logout
- Language switch between English and Telugu
- Theme toggle
- Current date display

### Buttons and Icons

- `Primary buttons` perform save, create, upload, approve, and submit actions
- `Outline buttons` are used for secondary actions such as view, back, clear, or cancel
- `Status badges` show petition state
- `Cards` present KPIs, analytics, and grouped actions

[Screenshot: Dashboard with Sidebar and Top Bar]  
Highlight:
- Sidebar navigation
- Top bar
- Notifications
- Profile menu

Caption:
Use the sidebar and top bar to move between modules and personal tools.

---

## Module-by-Module Guide

## Dashboard

### Purpose

The dashboard gives a role-based operational overview of petitions, recent work, trends, sources, types, and SLA indicators.

### How to Access

Click `Dashboard` in the sidebar.

### Main Functions

- Filter by date range, petition type, source, office, target CVO, and officer
- Review KPI cards and analytics charts
- Open recent petitions
- Drill down into metric cards and chart segments
- Open the SLA Dashboard

### Example Workflow

1. Open `Dashboard`.
2. Set a date range or additional filters.
3. Click `Apply`.
4. Review the KPI cards and charts.
5. Click a KPI card or chart area to open drilldown details.

## SLA Dashboard

### Purpose

The SLA Dashboard helps supervisors and managers monitor timeliness, workload, overdue petitions, and employee-wise SLA performance.

### How to Access

Click `SLA Dashboard` in the sidebar.

### Main Functions

- Review total, open, closed, within-SLA, and beyond-SLA metrics
- View charts for employee load, compliance, violations, and closures
- Open employee SLA profiles
- Drill down into SLA categories

### Example Workflow

1. Open `SLA Dashboard`.
2. Review KPI tiles.
3. Click any KPI tile to see related petitions.
4. Click an employee name to open the employee profile page.

## Petitions List

### Purpose

The Petitions module lists all petitions visible to the current user based on role and office scope.

### How to Access

Click `Petitions` in the sidebar.

### Main Functions

- Switch between `All`, `Direct`, and `Permission Based` modes
- Filter by status
- Open petition details
- Create a new petition if your role allows it

### Example Workflow

1. Open `Petitions`.
2. Select the required mode.
3. Select a status filter.
4. Click `View` or select a row to open petition details.

## New Petition

### Purpose

This screen captures a new petition, including petitioner details, source, type, office, target routing, remarks, and e-receipt details.

### How to Access

Click `New Petition` in the sidebar. This is available to Super Admin and Data Entry roles.

### Key Form Areas

- Received date and office
- E-receipt number and file
- Target CVO/DSP
- Permission request type
- Petitioner identity details
- Subject, type, source, and remarks

### Example Workflow

1. Open `New Petition`.
2. Enter the petition details.
3. Attach the E-receipt PDF if an E-receipt number is entered.
4. Click `Save Petition`.
5. The system creates the petition and routes it automatically according to the workflow.

## Petition Details

### Purpose

This is the central workflow page for viewing petition information, current status, enquiry report, attachments, and available role-based actions.

### How to Access

Open any petition from the dashboard or petitions list.

### Main Functions

- View petition details and workflow stage tracker
- View or download attached files
- Perform actions allowed for the current role
- Review enquiry report stages
- Review tracking history

### Example Workflow

1. Open a petition.
2. Review the petition information card.
3. Review the workflow stage tracker and current status.
4. Perform the next available action if assigned to you.
5. Review tracking history at the bottom of the page.

## User Management

### Purpose

This admin-only module manages user creation, password resets, inspector-to-CVO mapping, and activation status.

### How to Access

Click `User Management` in the sidebar. Available to Super Admin.

### Main Functions

- Create officer login
- Bulk create users via Excel or CSV
- Approve or reject password recovery requests
- Update user name, username, password, contact details, photo, mapping, and activation status

## Bulk Petition Import

### Purpose

This module imports historical petitions using a standard template.

### How to Access

Click `Bulk Petition Upload` in the sidebar. Available to PO.

### Main Functions

- Download template
- Upload `.xlsx` or `.csv` file
- Review exact field mapping rules

## Form Management

### Purpose

This admin-only module controls labels, field types, required flags, and dropdown values for dynamic forms.

### How to Access

Click `Form Management` in the sidebar. Available to Super Admin.

### Main Functions

- Choose form group and field
- Update label and field type
- Set required rule
- Edit dropdown options
- Add a new field

---

## Task-Based Instructions

## Task 1: Create a New Petition

**Goal:** Register a new petition and route it into the workflow.

1. Open `New Petition`.
2. Enter `Received Date`.
3. Select `Received At`.
4. Enter `E-Receipt No` if available.
5. Upload the `E-Receipt File` if an e-receipt number is entered.
6. Select `Target CVO/DSP` if applicable.
7. Select `Permission Request`.
8. Choose petitioner identity type.
9. Enter petitioner details if the petition is identified.
10. Enter the petition `Subject`.
11. Select `Type of Petition`.
12. Select `Source of Petition`.
13. If source is `Govt`, select `Type of Institution`.
14. Enter remarks if needed.
15. Click `Save Petition`.

[Screenshot: New Petition Entry Form]  
Highlight:
- Received Date
- Received At
- Target CVO/DSP
- Petition Type
- Source of Petition
- Save Petition

Expected Result:
The petition is saved, assigned a system number, and routed automatically.

Tips:
- If you enter an e-receipt number, you must upload the related PDF.
- Anonymous petitions hide petitioner, contact, and place fields.

## Task 2: Search and Filter Petitions

**Goal:** Find petitions by workflow mode or status.

1. Open `Petitions`.
2. Choose `All`, `Direct`, or `Permission Based`.
3. Use the `Filter` dropdown to select a status.
4. Review the filtered list.
5. Click `View` to open the required record.

[Screenshot: Petitions List Screen]  
Highlight:
- Mode selector
- Status filter
- Petition rows
- View button

Expected Result:
The list refreshes to show only matching petitions.

Tips:
- Use `Permission Based` when tracking approval-driven cases.
- Use `Direct` for direct enquiry cases.

## Task 3: Approve or Reject Permission as PO

**Goal:** Decide whether a petition should proceed under permission-based workflow.

1. Open the petition assigned to PO.
2. Review petition details and supporting documents.
3. If approving:
   1. Select target CVO/DSP.
   2. Select enquiry type if required.
   3. Enter `E-Office File No` if required by your form configuration.
   4. Add remarks if needed.
   5. Submit approval.
4. If rejecting:
   1. Enter rejection reason if required.
   2. Submit rejection.

[Screenshot: PO Permission Decision Area]  
Highlight:
- Approve action
- Reject action
- E-Office File No
- Remarks

Expected Result:
The petition moves forward to CVO/DSP or is marked as rejected.

Tips:
- JMD/PO routed cases may require organization selection.
- Rejection reason may be mandatory depending on form settings.

## Task 4: Assign a Petition to an Inspector

**Goal:** Send a petition to a field inspector for enquiry.

1. Open the petition as CVO/DSP.
2. Confirm that permission is approved if the case requires it.
3. Select the inspector.
4. Choose enquiry type if prompted.
5. Upload memo or instructions PDF if required.
6. Add comments if needed.
7. Submit the assignment.

[Screenshot: CVO Assign Inspector Section]  
Highlight:
- Inspector dropdown
- Enquiry type
- Memo upload
- Submit button

Expected Result:
The petition status changes to inspector assignment or enquiry progress state.

Tips:
- For direct enquiry, assignment is available when the petition is with CVO/DSP.
- For conversion workflows, the system may restrict reassignment to the previously assigned inspector.

## Task 5: Upload an Enquiry Report as Inspector

**Goal:** Submit the field enquiry report and supporting PDF.

1. Open the assigned petition.
2. If the petition is preliminary, select the next step:
   - `Send Report to CVO`
   - `Ask Permission to Convert to Detailed`
3. If reporting normally, enter:
   - Conclusion of enquiry report
   - Recommendations or suggestions
   - Enquiry report PDF
4. If the petition type is `Electrical Accident`, complete the accident details.
5. Click `Upload Report`.

[Screenshot: Inspector Report Upload Screen]  
Highlight:
- Report text
- Recommendation
- Report file upload
- Next step
- Upload Report

Expected Result:
The report is submitted and visible in the petition report section.

Tips:
- For preliminary enquiries, use conversion request only when a detailed enquiry is necessary.
- Electrical accident cases require additional category details.

## Task 6: Add CVO/DSP Comments

**Goal:** Review the inspector report and send the case onward.

1. Open the petition after report submission.
2. Review the uploaded report and recommendations.
3. Enter CVO comments.
4. Upload a consolidated report file if needed.
5. Forward the petition to PO or use the next applicable action.

[Screenshot: CVO Comment and Review Area]  
Highlight:
- CVO comments field
- Consolidated report file
- Forward action

Expected Result:
The petition moves to the next review stage with CVO observations recorded.

Tips:
- Media-source cases may allow direct lodge by CVO after report submission.

## Task 7: Submit CMD Action Report

**Goal:** Record action taken and send a copy back to PO for closure.

1. Open a petition in `Sent to CMD for Action` status.
2. Enter action taken details.
3. Upload the action report PDF.
4. Submit the action report.

[Screenshot: CMD Action Submission Screen]  
Highlight:
- Action taken text
- Action report upload
- Submit button

Expected Result:
The petition shows CMD action report submitted and returns to PO for final closure steps.

Tips:
- Only CMD or CGM/HR roles within scope can perform this action.

## Task 8: Monitor SLA Performance

**Goal:** Review SLA compliance at petition and employee level.

1. Open `SLA Dashboard`.
2. Review KPI cards for open, closed, within-SLA, and beyond-SLA counts.
3. Click a KPI card to open petition drilldown.
4. Click an employee name to open their SLA profile.

[Screenshot: SLA Dashboard Overview]  
Highlight:
- SLA KPI cards
- Employee grid
- Charts

Expected Result:
You can see workload, overdue cases, and employee-level compliance.

Tips:
- Use the employee profile page during supervisory review meetings.

## Task 9: Manage Users as Super Admin

**Goal:** Create, update, activate, or reset user accounts.

1. Open `User Management`.
2. To create a user:
   1. Fill username, password, officer name, and role.
   2. Add office or CVO mapping where required.
   3. Click `Create User`.
3. To manage an existing user:
   1. Select the user from the dropdown.
   2. Expand `Manage User`.
   3. Update the required information.
4. To process a password recovery request:
   1. Review the request in `Password Recovery Approvals`.
   2. Approve or reject the request.

[Screenshot: User Management Screen]  
Highlight:
- Create Officer Login
- Password Recovery Approvals
- Officer Directory & Controls

Expected Result:
The user account is created or updated successfully.

Tips:
- Inspectors should be mapped to the correct CVO/DSP.
- Inactive accounts remain in the directory but cannot log in.

## Task 10: Update Profile

**Goal:** Maintain your own personal login details.

1. Open `My Profile`.
2. Update name, username, phone, email, or password.
3. Upload or remove your photo if needed.
4. Click `Save Profile`.

[Screenshot: My Profile Screen]  
Highlight:
- Full Name
- Username
- New Password
- Profile Photo
- Save Profile

Expected Result:
Your profile is updated and stored successfully.

Tips:
- Leave the password fields blank if you do not want to change your password.

---

## Field Explanations

### Common Petition Form Fields

| Field | Description | Required | Notes |
|---|---|---|---|
| Received Date | Date the petition was received | Yes | Must be a valid date |
| Received At | Office where the petition was received | Yes | Valid options are limited to configured offices |
| E-Receipt No | Receipt reference number | Conditional | Required if an e-receipt PDF is uploaded |
| E-Receipt File | PDF copy of e-receipt | Conditional | Required if E-Receipt No is entered |
| Target CVO/DSP | Destination vigilance office | Conditional | Required except for JMD/PO route cases |
| Permission Request | Direct or permission-based routing | Conditional | Not shown in all flows |
| Petitioner Identity | Identified or anonymous | No | Anonymous hides petitioner details |
| Petitioner Name | Name of petitioner | Conditional | Hidden for anonymous petitions |
| Contact Number | Contact phone | Conditional | Valid phone format required when entered |
| Place | Location or area | Conditional | Hidden for anonymous petitions |
| Subject | Petition subject or summary | Yes | Length validation applies |
| Type of Petition | Nature of complaint | Yes | Must be one of the system options |
| Source of Petition | Origin of petition | Yes | Includes public, media, govt, sumoto, and some office-specific options |
| Govt Institution Type | Institution category for government source | Conditional | Used only when source is Govt |
| Remarks | Additional notes | Optional or required by configuration | Can be made mandatory in Form Management |

### Petition Type Values

- Bribe
- Corruption
- Harassment
- Electrical Accident
- Misconduct
- Works Related
- Irregularities in Tenders
- Illegal Assets
- Fake Certificates
- Theft/Misappropriation of Materials
- Other

### Source of Petition Values

- Electronic and Print Media
- Public (Individual)
- Govt
- Sumoto
- O/o CMD

### Validation Rules

- File uploads for petition workflow documents must be PDF
- Maximum configured file size is 10 MB
- Phone number must be in a valid contact format
- Email address must be valid when entered
- Required fields depend on system configuration and workflow context
- CSRF validation is enforced for form submissions

---

## Error Handling

| Error | Possible Cause | Solution |
|---|---|---|
| Invalid action request | The submitted action is missing or unsupported | Refresh the page and try again |
| You do not have access to this petition | Role or scope does not allow access | Open only petitions assigned to your role/scope |
| Please select a valid target CVO/DSP | Target office is blank or not valid | Re-select a valid destination office |
| E-Receipt file is required when E-Receipt No is provided | Number entered without file upload | Upload the matching PDF and submit again |
| E-Receipt No is required when uploading E-Receipt file | File uploaded without receipt number | Enter the receipt number before saving |
| Upload exceeds 10 MB limit | File is larger than allowed size | Compress or replace the file |
| Please provide a valid phone number | Phone format failed validation | Correct the number and submit again |
| Please provide a valid email address | Email format failed validation | Correct the email and submit again |
| Recovery session expired. Please login again. | Recovery window ended | Return to login and restart |
| Contact admin to update phone number | The account lacks a usable recovery phone number | Ask admin to update your profile |
| Only PO can approve permission | Wrong user role attempted PO action | Log in with the correct role or reassign the task |
| Permission is compulsory. PO approval required before assigning inspector | Case needs approval before field assignment | Wait for PO approval first |

---

## Troubleshooting

### I cannot log in

- Confirm your username and password
- Check the CAPTCHA answer
- Verify that your phone number is correct in the system
- If repeated failures occur, wait for lockout expiry or contact admin

### My petition is not visible

- Check whether it is outside your role or office scope
- Check the current mode and status filters
- Ask the administrator to confirm routing and assignment

### I cannot upload a file

- Confirm the file is PDF where PDF is required
- Confirm the file is under 10 MB
- Try renaming the file and uploading again

### The wrong fields are appearing in a form

- Some fields change based on source, identity type, role, or workflow stage
- If the issue is persistent, ask the Super Admin to review Form Management configuration

### Recovery is not available

- Confirm the registered phone number
- Restart the recovery flow
- If it still fails, contact the administrator

---

## Frequently Asked Questions (FAQ)

### Can anonymous petitions be entered?

Yes. Select `Anonymous Petition` in the petitioner identity field. Petitioner, contact, and place fields are then hidden.

### Can I upload non-PDF files?

For core workflow documents such as e-receipts, memos, enquiry reports, and action reports, the system expects PDF files.

### Who can create new petitions?

Super Admin and Data Entry users can create new petitions from the application menu.

### Who can manage users?

Only Super Admin can access the User Management and Form Management modules.

### Can CVO directly lodge a petition?

Yes, for eligible Electronic and Print Media cases after the enquiry report is submitted.

### What happens if an SLA is exceeded?

The petition appears in beyond-SLA metrics and dashboards for operational monitoring and follow-up.

### Can old petitions be imported?

Yes. PO users can use the `Bulk Petition Upload` module with the system template.

---

## Glossary

| Term | Meaning |
|---|---|
| Petition | A complaint, vigilance case, or matter entered into the system |
| CVO | Chief Vigilance Officer |
| DSP | Deputy Superintendent of Police |
| PO | Personal Officer (Vigilance) |
| Inspector | Field investigation officer such as CI or SI |
| E-Receipt | Reference number and scanned receipt related to the petition |
| E-Office File No | Official file number used in downstream office processing |
| Direct Enquiry | A route where CVO/DSP proceeds without prior PO permission |
| Permission Based | A route where PO approval is required before enquiry proceeds |
| SLA | Service Level Agreement, used here for petition handling time targets |
| Tracking History | Chronological audit trail of petition actions |
| Lodged | Petition moved into formal recorded disposition stage |
| Closed | Petition workflow completed |

---

## Support Information

### Support Contact

- Helpdesk/Team: `[Insert Support Team Name]`
- Email: `[Insert Support Email]`
- Phone: `[Insert Support Phone]`
- Support Hours: `[Insert Support Hours]`

### Escalation Process

1. Contact first-line application support.
2. If not resolved, escalate to system administrator or vigilance IT coordinator.
3. If the issue is workflow-critical, escalate to the application owner or approving authority.

### Information Users Should Provide

When requesting support, provide:

- Username
- Role
- Petition number or screen name
- Date and time of issue
- Error message text
- Screenshot, if available
- Browser name

---

## Screenshot Capture Checklist

| Screen Name | Purpose | Highlight Elements | Suggested Filename |
|---|---|---|---|
| Login Page | Show system sign-in flow | Username, Password, CAPTCHA, Sign In | `01-login-page.png` |
| Password Reset | Allow account recovery | Username check and password reset form | `02-password-reset.png` |
| Dashboard | Show landing workspace | Sidebar, KPI cards, charts, recent petitions | `03-dashboard-overview.png` |
| Dashboard Filters | Explain data filtering | From date, To date, filter options, Apply | `04-dashboard-filters.png` |
| Petitions List | Show petition browsing | Mode pills, status filter, table, View | `05-petitions-list.png` |
| New Petition Form | Show petition creation | Key fields and Save Petition button | `06-new-petition-form.png` |
| Govt Source Form | Explain conditional fields | Source of Petition, Govt Institution Type | `07-petition-govt-fields.png` |
| Anonymous Petition Form | Explain anonymous flow | Petitioner Identity, hidden details area | `08-petition-anonymous.png` |
| Petition Details | Show record review page | S.No, status badge, workflow stages | `09-petition-details.png` |
| Tracking History | Show audit trail | Timeline items, comments, attachment links | `10-tracking-history.png` |
| CVO Routing/Assignment | Show CVO work area | Enquiry mode, inspector dropdown, memo upload | `11-cvo-routing-assignment.png` |
| PO Decision | Show permission workflow | Approve, Reject, E-Office File No, remarks | `12-po-permission-decision.png` |
| Inspector Report Upload | Show report submission | Report text, recommendation, PDF upload | `13-inspector-report-upload.png` |
| Electrical Accident Fields | Show special-case reporting | Accident type, category, counts | `14-electrical-accident-fields.png` |
| Report Stage View | Show report review chain | CI report, recommendations, CVO comments | `15-report-stage-view.png` |
| CMD Action Screen | Show action report step | Action taken text, report upload | `16-cmd-action-report.png` |
| SLA Dashboard | Show SLA oversight | SLA KPIs, employee grid, charts | `17-sla-dashboard.png` |
| SLA Employee Profile | Show officer-level detail | Totals, compliance, petition list | `18-sla-employee-profile.png` |
| User Management | Show admin landing page | Create user, approvals, user controls | `19-user-management.png` |
| Bulk User Upload | Show batch user setup | Upload file field, notes | `20-bulk-user-upload.png` |
| Password Recovery Queue | Show approval process | Pending requests, approve/reject actions | `21-password-recovery-queue.png` |
| Officer Directory | Show user maintenance | User picker, manage user cards | `22-officer-directory.png` |
| My Profile | Show self-service profile page | Name, username, password, photo | `23-my-profile.png` |
| Bulk Petition Import | Show legacy import process | Template download, upload button, field mapping | `24-bulk-petition-import.png` |
| Form Management | Show dynamic field administration | Form group, field editor, save field | `25-form-management.png` |
| Notifications Menu | Show pending work access | Bell icon, counts, petition links | `26-notifications-menu.png` |
| Petitioner Profile Modal | Show petitioner insight | KPI cards, charts, recent petitions | `27-petitioner-profile-modal.png` |

---

## Suggested UI Documentation Improvements

1. Add fixed field-level help text for `Direct` versus `Permission Based` routing because that decision drives major workflow differences.
2. Add an always-visible legend for petition statuses and workflow stage names.
3. Show role-specific quick help on the Petition Details page so users know what action is expected next.
4. Add inline examples for `Govt Institution Type`, `Source of Petition`, and `Petition Type`.
5. Add a visible upload rule note beside every PDF upload field, including max size and allowed format.
6. Add contextual help for preliminary-to-detailed conversion requests.
7. Add an on-screen tooltip or help panel in SLA Dashboard to explain `Within SLA`, `Beyond SLA`, and `In Progress`.
8. Add a compact "Who can do this action?" note above action panels in the petition workflow.

---

## Optional Training Guide

### Recommended Training Audience

- Data Entry Operators
- PO users
- CVO/DSP users
- Inspectors
- Super Admins

### Suggested Training Sessions

| Session | Audience | Duration | Topics |
|---|---|---|---|
| Session 1 | All users | 45 min | Login, navigation, dashboard, petition search |
| Session 2 | Data Entry + PO | 60 min | Petition creation, routing, approval flow |
| Session 3 | CVO/DSP + Inspectors | 60 min | Assignment, report upload, review actions |
| Session 4 | PO + CMD/CGM | 45 min | Closure, action reports, SLA interpretation |
| Session 5 | Super Admin | 60 min | User Management, Form Management, password recovery |

### Practice Scenarios

1. Create an identified petition and route it to a CVO/DSP office.
2. Create an anonymous petition from JMD/PO office flow.
3. Approve a permission-based case as PO.
4. Assign an inspector and upload a report.
5. Review an SLA breach case and open the employee profile.
6. Create a user and process a password recovery request.

### Training Deliverables

- This user manual
- Screenshot deck
- Role-wise quick reference sheets
- Sample petitions for hands-on practice
