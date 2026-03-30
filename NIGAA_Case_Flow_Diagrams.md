# NIGAA Petition Tracker - Case Flow Diagrams

> Complete visualization of petition workflows, user roles, status transitions, and case routing paths.

---

## Table of Contents

1. [User Roles Overview](#1-user-roles-overview)
2. [Master Petition Lifecycle](#2-master-petition-lifecycle)
3. [Path A: Direct Enquiry Flow](#3-path-a-direct-enquiry-flow-no-permission-required)
4. [Path B: Permission-Based Flow](#4-path-b-permission-based-flow-po-approval-required)
5. [DEO (Data Entry Operator) Flow](#5-deo-data-entry-operator-flow)
6. [CVO / DSP Flow](#6-cvo--dsp-flow)
7. [Field Inspector Flow](#7-field-inspector-flow)
8. [Personal Officer (PO) Flow](#8-personal-officer-po-flow)
9. [CMD / CGM-HR Flow](#9-cmd--cgm-hr-flow)
10. [Preliminary to Detailed Enquiry Conversion](#10-preliminary-to-detailed-enquiry-conversion)
11. [Media Source - Direct Lodge Flow](#11-media-source---direct-lodge-flow)
12. [Beyond SLA Escalation Flow](#12-beyond-sla-escalation-flow)
13. [PO Direct Lodge (No Enquiry Needed)](#13-po-direct-lodge-no-enquiry-needed)
14. [Complete Status Transition Matrix](#14-complete-status-transition-matrix)
15. [6-Stage Workflow Summary](#15-6-stage-workflow-summary)
16. [SLA Timelines](#16-sla-timelines)

---

## 1. User Roles Overview

```mermaid
graph TD
    subgraph "NIGAA User Roles & Hierarchy"
        SA["Super Admin<br/>---<br/>Full system access<br/>User management<br/>Form configuration"]

        DEO["Data Entry Operator<br/>---<br/>Creates petitions<br/>Routes to CVO/DSP/PO"]

        PO["Personal Officer (PO)<br/>---<br/>Permission approval<br/>Case conclusion<br/>Lodge & close cases<br/>Instruct CMD action"]

        CVO1["CVO APSPDCL<br/>---<br/>Field investigation<br/>Inspector assignment<br/>Report review"]
        CVO2["CVO APEPDCL<br/>---<br/>Field investigation<br/>Inspector assignment<br/>Report review"]
        CVO3["CVO APCPDCL<br/>---<br/>Field investigation<br/>Inspector assignment<br/>Report review"]
        DSP["DSP (HQ)<br/>---<br/>HQ-level cases<br/>Inspector assignment<br/>Report review"]

        FI["Field Inspector (CI/SI)<br/>---<br/>Conducts field enquiry<br/>Submits investigation report"]

        CMD["CMD (Org Level)<br/>---<br/>Executes action<br/>per PO instructions"]

        CGM["CGM/HR TRANSCO<br/>---<br/>Executes action<br/>for HQ-scope cases"]
    end

    SA --> DEO
    SA --> PO
    DEO -->|forwards to| CVO1
    DEO -->|forwards to| CVO2
    DEO -->|forwards to| CVO3
    DEO -->|forwards to| DSP
    CVO1 -->|assigns| FI
    CVO2 -->|assigns| FI
    CVO3 -->|assigns| FI
    DSP -->|assigns| FI
    FI -->|reports to| CVO1
    FI -->|reports to| CVO2
    FI -->|reports to| CVO3
    FI -->|reports to| DSP
    CVO1 -->|forwards to| PO
    CVO2 -->|forwards to| PO
    CVO3 -->|forwards to| PO
    DSP -->|forwards to| PO
    PO -->|instructs| CMD
    PO -->|instructs| CGM

    style SA fill:#e74c3c,color:#fff
    style DEO fill:#3498db,color:#fff
    style PO fill:#9b59b6,color:#fff
    style CVO1 fill:#e67e22,color:#fff
    style CVO2 fill:#e67e22,color:#fff
    style CVO3 fill:#e67e22,color:#fff
    style DSP fill:#e67e22,color:#fff
    style FI fill:#27ae60,color:#fff
    style CMD fill:#1abc9c,color:#fff
    style CGM fill:#1abc9c,color:#fff
```

---

## 2. Master Petition Lifecycle

> This is the complete overview showing ALL possible paths a petition can take.

```mermaid
flowchart TD
    START(("Petition<br/>Created")) --> RECEIVED["RECEIVED<br/>(DEO creates petition)"]

    RECEIVED -->|"DEO forwards<br/>to CVO/DSP"| FWD_CVO["FORWARDED TO CVO/DSP"]

    FWD_CVO -->|"Direct Enquiry<br/>(no permission needed)"| ASSIGN["ASSIGNED TO INSPECTOR"]
    FWD_CVO -->|"Permission Required<br/>(CVO sends to PO)"| SENT_PERM["SENT FOR PERMISSION"]

    SENT_PERM -->|"PO Approves"| PERM_APPROVED["PERMISSION APPROVED"]
    SENT_PERM -->|"PO Rejects"| PERM_REJECTED["PERMISSION REJECTED"]
    SENT_PERM -->|"PO Direct Lodge<br/>(no enquiry needed)"| LODGED["LODGED"]

    PERM_APPROVED -->|"CVO assigns<br/>inspector"| ASSIGN
    PERM_REJECTED --> END_REJECTED(("Case<br/>Rejected"))

    ASSIGN -->|"Inspector conducts<br/>field enquiry"| REPORT_SUB["ENQUIRY REPORT<br/>SUBMITTED"]

    REPORT_SUB -->|"CVO adds<br/>comments"| CVO_COMMENTS["CVO COMMENTS<br/>ADDED"]
    REPORT_SUB -->|"CVO sends back<br/>for re-enquiry"| REENQUIRY["SENT BACK FOR<br/>RE-ENQUIRY"]
    REPORT_SUB -->|"CVO direct lodge<br/>(media cases)"| LODGED
    REPORT_SUB -->|"Request conversion<br/>preliminary to detailed"| CONV["CONVERSION<br/>REQUESTED"]

    REENQUIRY -->|"Inspector re-investigates<br/>& resubmits"| REPORT_SUB

    CVO_COMMENTS -->|"CVO forwards<br/>to PO"| FWD_PO["FORWARDED TO PO"]
    REPORT_SUB -->|"CVO forwards<br/>to PO directly"| FWD_PO

    CONV -->|"Goes back to<br/>PO for permission"| SENT_PERM

    FWD_PO -->|"PO gives conclusion<br/>& closes"| CLOSED["CLOSED"]
    FWD_PO -->|"PO lodges"| LODGED
    FWD_PO -->|"PO instructs<br/>CMD/CGM-HR"| ACTION_INST["ACTION INSTRUCTED"]
    FWD_PO -->|"PO sends back<br/>for re-enquiry"| REENQUIRY_PO["SENT BACK FOR<br/>RE-ENQUIRY (via CVO)"]

    REENQUIRY_PO -->|"CVO reassigns<br/>to inspector"| ASSIGN

    ACTION_INST -->|"CMD/CGM-HR<br/>submits action report"| ACTION_TAKEN["ACTION TAKEN"]

    ACTION_TAKEN -->|"PO lodges"| LODGED
    ACTION_TAKEN -->|"PO gives conclusion<br/>& closes"| CLOSED

    LODGED -->|"PO closes"| CLOSED

    CLOSED --> END_CLOSED(("Case<br/>Closed"))

    style START fill:#2c3e50,color:#fff
    style RECEIVED fill:#3498db,color:#fff
    style FWD_CVO fill:#e67e22,color:#fff
    style SENT_PERM fill:#f39c12,color:#fff
    style PERM_APPROVED fill:#27ae60,color:#fff
    style PERM_REJECTED fill:#e74c3c,color:#fff
    style ASSIGN fill:#27ae60,color:#fff
    style REPORT_SUB fill:#16a085,color:#fff
    style CVO_COMMENTS fill:#e67e22,color:#fff
    style FWD_PO fill:#9b59b6,color:#fff
    style REENQUIRY fill:#e74c3c,color:#fff
    style REENQUIRY_PO fill:#e74c3c,color:#fff
    style CONV fill:#f39c12,color:#fff
    style ACTION_INST fill:#1abc9c,color:#fff
    style ACTION_TAKEN fill:#1abc9c,color:#fff
    style LODGED fill:#8e44ad,color:#fff
    style CLOSED fill:#2c3e50,color:#fff
    style END_CLOSED fill:#2c3e50,color:#fff
    style END_REJECTED fill:#e74c3c,color:#fff
```

---

## 3. Path A: Direct Enquiry Flow (No Permission Required)

> Used when the petition type does not require PO approval before investigation.

```mermaid
flowchart TD
    A1["DEO Creates Petition<br/>permission_request_type = 'direct_enquiry'"]
    A2["Status: RECEIVED"]
    A3["DEO Forwards to CVO/DSP<br/>(selects target office)"]
    A4["Status: FORWARDED TO CVO/DSP"]
    A5["CVO/DSP Receives Petition<br/>Sets E-Receipt Number<br/>Selects Enquiry Type:<br/>Detailed or Preliminary"]
    A6["CVO/DSP Assigns Field Inspector<br/>Uploads Memo/Instructions"]
    A7["Status: ASSIGNED TO INSPECTOR"]
    A8["Inspector Conducts<br/>Field Investigation"]
    A9["Inspector Submits Report<br/>- Conclusion of Enquiry<br/>- Recommendations<br/>- Report PDF"]
    A10["Status: ENQUIRY REPORT SUBMITTED"]
    A11["CVO/DSP Reviews Report<br/>- Adds Comments<br/>- Uploads Consolidated Report"]
    A12["Status: CVO COMMENTS ADDED"]
    A13["CVO/DSP Forwards to PO"]
    A14["Status: FORWARDED TO PO"]
    A15{"PO Decision"}
    A16["PO Gives Conclusion<br/>& Closes Case"]
    A17["PO Instructs CMD/CGM-HR<br/>for Action"]
    A18["Status: ACTION INSTRUCTED"]
    A19["CMD/CGM-HR Takes Action<br/>Submits Action Report"]
    A20["Status: ACTION TAKEN"]
    A21["PO Lodges Petition"]
    A22["Status: LODGED"]
    A23["PO Closes Petition"]
    A24["Status: CLOSED"]

    A1 --> A2 --> A3 --> A4 --> A5 --> A6 --> A7 --> A8 --> A9 --> A10 --> A11 --> A12 --> A13 --> A14 --> A15

    A15 -->|"Conclusion Only"| A16 --> A24
    A15 -->|"Action Needed"| A17 --> A18 --> A19 --> A20 --> A21 --> A22 --> A23 --> A24
    A15 -->|"Direct Lodge"| A21

    style A1 fill:#3498db,color:#fff
    style A2 fill:#3498db,color:#fff
    style A4 fill:#e67e22,color:#fff
    style A7 fill:#27ae60,color:#fff
    style A10 fill:#16a085,color:#fff
    style A12 fill:#e67e22,color:#fff
    style A14 fill:#9b59b6,color:#fff
    style A18 fill:#1abc9c,color:#fff
    style A20 fill:#1abc9c,color:#fff
    style A22 fill:#8e44ad,color:#fff
    style A24 fill:#2c3e50,color:#fff
```

---

## 4. Path B: Permission-Based Flow (PO Approval Required)

> Used when the petition requires PO permission before CVO/DSP can begin investigation.

```mermaid
flowchart TD
    B1["DEO Creates Petition<br/>permission_request_type = 'permission_required'"]
    B2["Status: RECEIVED"]
    B3["DEO Forwards to CVO/DSP"]
    B4["Status: FORWARDED TO CVO/DSP"]
    B5["CVO/DSP Sets E-Receipt<br/>Uploads Permission Memo"]
    B6["CVO/DSP Sends for Permission"]
    B7["Status: SENT FOR PERMISSION"]

    B8{"PO Reviews<br/>Permission Request"}

    B9["PO Approves Permission<br/>- Selects target CVO<br/>- Sets E-Office File No<br/>- Selects Enquiry Type"]
    B10["Status: PERMISSION APPROVED"]

    B11["PO Rejects Permission<br/>with Reason"]
    B12["Status: PERMISSION REJECTED"]
    B13(("Case Ends"))

    B14["CVO/DSP Assigns Inspector<br/>Uploads Memo"]
    B15["Status: ASSIGNED TO INSPECTOR"]

    B16["Inspector Conducts Enquiry<br/>& Submits Report"]
    B17["Status: ENQUIRY REPORT SUBMITTED"]

    B18["CVO/DSP Reviews & Comments"]
    B19["CVO/DSP Forwards to PO"]
    B20["Status: FORWARDED TO PO"]

    B21{"PO Decision"}
    B22["Conclusion & Close"]
    B23["Instruct CMD Action"]
    B24["Lodge & Close"]
    B25["Status: CLOSED"]

    B1 --> B2 --> B3 --> B4 --> B5 --> B6 --> B7 --> B8

    B8 -->|"Approve"| B9 --> B10 --> B14 --> B15 --> B16 --> B17 --> B18 --> B19 --> B20 --> B21
    B8 -->|"Reject"| B11 --> B12 --> B13
    B8 -->|"Direct Lodge<br/>(no enquiry needed)"| B24

    B21 -->|"Conclusion"| B22 --> B25
    B21 -->|"Action Needed"| B23 -->|"CMD acts & returns"| B24
    B21 -->|"Lodge"| B24 --> B25

    style B1 fill:#3498db,color:#fff
    style B4 fill:#e67e22,color:#fff
    style B7 fill:#f39c12,color:#fff
    style B10 fill:#27ae60,color:#fff
    style B12 fill:#e74c3c,color:#fff
    style B15 fill:#27ae60,color:#fff
    style B17 fill:#16a085,color:#fff
    style B20 fill:#9b59b6,color:#fff
    style B25 fill:#2c3e50,color:#fff
```

---

## 5. DEO (Data Entry Operator) Flow

> Detailed view of all actions available to the Data Entry Operator.

```mermaid
flowchart TD
    DEO_START(("DEO Logs In"))
    DEO1["Navigate to<br/>Create New Petition"]
    DEO2["Fill Petition Form:<br/>- S.No (auto: VIG/JMD/YYYY/NNNN)<br/>- Received Date<br/>- Petitioner Name & Contact<br/>- Subject & Petition Type<br/>- Source of Petition<br/>- Target CVO/DSP Office<br/>- Organization<br/>- Remarks<br/>- Permission Type: Direct/Permission"]
    DEO3["Submit Petition"]
    DEO4["Status: RECEIVED"]

    DEO5{"Route Decision"}
    DEO6["Forward to Target CVO/DSP"]
    DEO7["Auto-route JMD Office<br/>petitions to PO"]

    DEO8["Status: FORWARDED TO CVO/DSP"]
    DEO9["DEO can view petition<br/>status on dashboard"]

    DEO_BULK["Bulk Import Petitions<br/>(CSV/Excel Upload)"]

    DEO_START --> DEO1 --> DEO2 --> DEO3 --> DEO4 --> DEO5
    DEO5 -->|"Standard"| DEO6 --> DEO8
    DEO5 -->|"JMD Office"| DEO7
    DEO_START --> DEO_BULK
    DEO8 --> DEO9

    style DEO_START fill:#2c3e50,color:#fff
    style DEO4 fill:#3498db,color:#fff
    style DEO8 fill:#e67e22,color:#fff
    style DEO_BULK fill:#3498db,color:#fff
```

---

## 6. CVO / DSP Flow

> Detailed view of all actions available to CVO/DSP officers at each status.

```mermaid
flowchart TD
    CVO_START(("CVO/DSP<br/>Receives Petition"))

    CVO1["Status: FORWARDED TO CVO/DSP"]
    CVO2{"Permission Type?"}

    subgraph "Direct Enquiry Path"
        CVO3["Set E-Receipt Number<br/>Upload E-Receipt File"]
        CVO4["Select Enquiry Type:<br/>Detailed / Preliminary"]
        CVO5["Assign Field Inspector<br/>Upload Memo/Instructions"]
        CVO6["Status: ASSIGNED TO INSPECTOR"]
    end

    subgraph "Permission Path"
        CVO7["Set E-Receipt Number"]
        CVO8["Upload Permission Memo"]
        CVO9["Send for Permission to PO"]
        CVO10["Status: SENT FOR PERMISSION"]
        CVO11["Wait for PO Decision..."]
        CVO12["Status: PERMISSION APPROVED"]
        CVO13["Assign Inspector<br/>Upload Memo"]
    end

    CVO14["Wait for Inspector Report..."]
    CVO15["Status: ENQUIRY REPORT SUBMITTED"]

    CVO16{"CVO Review Options"}
    CVO17["Add CVO Comments<br/>Upload Consolidated Report"]
    CVO18["Forward to PO"]
    CVO19["Send Back for Re-Enquiry<br/>(same inspector)"]
    CVO20["Direct Lodge<br/>(MEDIA cases only)"]
    CVO21["Request Detailed Enquiry<br/>(conversion from preliminary)"]

    CVO22["Status: FORWARDED TO PO"]
    CVO23["Status: SENT BACK FOR RE-ENQUIRY"]
    CVO24["Status: LODGED"]

    CVO_START --> CVO1 --> CVO2
    CVO2 -->|"Direct"| CVO3 --> CVO4 --> CVO5 --> CVO6
    CVO2 -->|"Permission Required"| CVO7 --> CVO8 --> CVO9 --> CVO10 --> CVO11 --> CVO12 --> CVO13 --> CVO6

    CVO6 --> CVO14 --> CVO15 --> CVO16

    CVO16 -->|"Review & Forward"| CVO17 --> CVO18 --> CVO22
    CVO16 -->|"Re-Enquiry"| CVO19 --> CVO23 -->|"Inspector resubmits"| CVO15
    CVO16 -->|"Media Lodge"| CVO20 --> CVO24
    CVO16 -->|"Convert Enquiry"| CVO21 -->|"Back to PO"| CVO10

    style CVO_START fill:#2c3e50,color:#fff
    style CVO1 fill:#e67e22,color:#fff
    style CVO6 fill:#27ae60,color:#fff
    style CVO10 fill:#f39c12,color:#fff
    style CVO12 fill:#27ae60,color:#fff
    style CVO15 fill:#16a085,color:#fff
    style CVO22 fill:#9b59b6,color:#fff
    style CVO23 fill:#e74c3c,color:#fff
    style CVO24 fill:#8e44ad,color:#fff
```

---

## 7. Field Inspector Flow

> Detailed view of the field inspector's investigation and reporting workflow.

```mermaid
flowchart TD
    FI_START(("Inspector<br/>Receives Assignment"))
    FI1["Status: ASSIGNED TO INSPECTOR"]
    FI2["View Assignment Details:<br/>- Petition Subject<br/>- Petition Type<br/>- CVO Memo/Instructions<br/>- Enquiry Type"]

    FI3["Conduct Field Investigation"]

    FI4{"Petition Type?"}

    subgraph "Standard Report"
        FI5["Fill Report:<br/>- Conclusion of Enquiry<br/>- Recommendations/Suggestions<br/>- Upload Report PDF"]
    end

    subgraph "Electrical Accident Report"
        FI6["Fill Report + Accident Details:<br/>- Accident Type (Departmental/<br/>  Non-Departmental)<br/>- Deceased Category<br/>- Deceased Count<br/>- Department Type Details<br/>- General Public / Animals Count<br/>- Upload Report PDF"]
    end

    FI7{"Enquiry Type = Preliminary?"}
    FI8["Option: Request Conversion<br/>to Detailed Enquiry<br/>- Provide Reason for Conversion"]
    FI9["Submit Report"]
    FI10["Status: ENQUIRY REPORT SUBMITTED"]

    FI11["Wait for CVO Decision..."]
    FI12{"CVO sends back<br/>for re-enquiry?"}
    FI13["Status: SENT BACK FOR RE-ENQUIRY"]
    FI14["Re-investigate &<br/>Submit Updated Report"]
    FI15["Case moves forward<br/>to PO"]

    FI_START --> FI1 --> FI2 --> FI3 --> FI4
    FI4 -->|"Standard"| FI5 --> FI7
    FI4 -->|"Electrical Accident"| FI6 --> FI7

    FI7 -->|"Yes"| FI8 --> FI9
    FI7 -->|"No (Detailed)"| FI9
    FI9 --> FI10 --> FI11 --> FI12

    FI12 -->|"Yes"| FI13 --> FI14 --> FI10
    FI12 -->|"No"| FI15

    style FI_START fill:#2c3e50,color:#fff
    style FI1 fill:#27ae60,color:#fff
    style FI10 fill:#16a085,color:#fff
    style FI13 fill:#e74c3c,color:#fff
    style FI15 fill:#9b59b6,color:#fff
```

---

## 8. Personal Officer (PO) Flow

> Detailed view of all actions available to the PO at each stage.

```mermaid
flowchart TD
    PO_START(("PO Receives<br/>Petition"))

    subgraph "Permission Stage"
        PO1["Status: SENT FOR PERMISSION"]
        PO2{"PO Permission<br/>Decision"}
        PO3["APPROVE Permission<br/>- Select Target CVO<br/>- Set E-Office File No<br/>- Select Enquiry Type"]
        PO4["REJECT Permission<br/>- Provide Rejection Reason"]
        PO5["DIRECT LODGE<br/>(No enquiry needed)"]
        PO6["BEYOND SLA SEND TO CVO<br/>(>90 days escalation)"]
    end

    PO7["Status: PERMISSION APPROVED<br/>Back to CVO for assignment"]
    PO8["Status: PERMISSION REJECTED<br/>Case Ends"]
    PO9["Status: LODGED"]

    subgraph "Review Stage"
        PO10["Status: FORWARDED TO PO"]
        PO11{"PO Review<br/>Decision"}
        PO12["GIVE CONCLUSION<br/>- Provide final conclusion<br/>- Upload conclusion file<br/>- Case CLOSED"]
        PO13["INSTRUCT CMD ACTION<br/>- Send to CMD/CGM-HR<br/>- Provide instructions"]
        PO14["LODGE PETITION<br/>- Provide lodge remarks"]
        PO15["SEND BACK RE-ENQUIRY<br/>- Back to CVO/Inspector"]
        PO16["UPDATE E-FILE NO<br/>(Direct enquiry cases)"]
    end

    PO17["Status: ACTION INSTRUCTED"]
    PO18["CMD/CGM-HR takes action..."]
    PO19["Status: ACTION TAKEN"]

    PO20{"PO Final Action"}
    PO21["Lodge & Close"]
    PO22["Give Conclusion & Close"]

    PO23["Status: CLOSED"]

    PO_START --> PO1 --> PO2
    PO2 -->|"Approve"| PO3 --> PO7
    PO2 -->|"Reject"| PO4 --> PO8
    PO2 -->|"Direct Lodge"| PO5 --> PO9
    PO2 -->|"SLA Escalation"| PO6

    PO_START --> PO10 --> PO11
    PO11 -->|"Conclude"| PO12 --> PO23
    PO11 -->|"Action Needed"| PO13 --> PO17 --> PO18 --> PO19 --> PO20
    PO11 -->|"Lodge"| PO14 --> PO9 --> PO23
    PO11 -->|"Re-Enquiry"| PO15
    PO11 -->|"Update E-File"| PO16

    PO20 -->|"Lodge"| PO21 --> PO23
    PO20 -->|"Conclude"| PO22 --> PO23

    style PO_START fill:#2c3e50,color:#fff
    style PO1 fill:#f39c12,color:#fff
    style PO7 fill:#27ae60,color:#fff
    style PO8 fill:#e74c3c,color:#fff
    style PO9 fill:#8e44ad,color:#fff
    style PO10 fill:#9b59b6,color:#fff
    style PO17 fill:#1abc9c,color:#fff
    style PO19 fill:#1abc9c,color:#fff
    style PO23 fill:#2c3e50,color:#fff
```

---

## 9. CMD / CGM-HR Flow

> Detailed view of the CMD/CGM-HR action execution workflow.

```mermaid
flowchart TD
    CMD_START(("CMD/CGM-HR<br/>Receives Instruction"))
    CMD1["Status: ACTION INSTRUCTED"]
    CMD2["View PO Instructions:<br/>- Petition Details<br/>- Enquiry Report<br/>- CVO Comments<br/>- PO Instructions"]
    CMD3["Execute Required Action"]
    CMD4["Submit Action Report:<br/>- Action Taken Details<br/>- Upload Action Report PDF"]
    CMD5["Status: ACTION TAKEN"]
    CMD6["Petition Returns to PO<br/>for Final Decision"]

    CMD_START --> CMD1 --> CMD2 --> CMD3 --> CMD4 --> CMD5 --> CMD6

    style CMD_START fill:#2c3e50,color:#fff
    style CMD1 fill:#1abc9c,color:#fff
    style CMD5 fill:#1abc9c,color:#fff
    style CMD6 fill:#9b59b6,color:#fff
```

---

## 10. Preliminary to Detailed Enquiry Conversion

> Special flow when a preliminary enquiry needs to be upgraded to a detailed enquiry.

```mermaid
flowchart TD
    CONV1["Inspector is assigned<br/>PRELIMINARY enquiry"]
    CONV2["Inspector conducts<br/>preliminary investigation"]
    CONV3["Inspector submits report<br/>with CONVERSION REQUEST<br/>- Provides detailed reason"]
    CONV4["Status: ENQUIRY REPORT SUBMITTED<br/>(request_detailed_permission = TRUE)"]

    CONV5["CVO Reviews Conversion Request"]
    CONV6{"CVO Decision"}

    CONV7["CVO Approves Conversion<br/>- Adds remarks<br/>- Forwards to PO for permission"]
    CONV8["Status: SENT FOR PERMISSION<br/>(conversion context)"]

    CONV9{"PO Decision<br/>on Conversion"}
    CONV10["PO APPROVES<br/>- Sets E-Office File No<br/>- Enquiry Type = Detailed"]
    CONV11["Status: PERMISSION APPROVED"]

    CONV12["CVO Re-assigns SAME Inspector<br/>(conversion lock enforced)<br/>Enquiry Type: DETAILED"]
    CONV13["Status: ASSIGNED TO INSPECTOR"]
    CONV14["Inspector conducts<br/>DETAILED enquiry"]
    CONV15["Inspector submits<br/>detailed report"]
    CONV16["Normal flow continues..."]

    CONV1 --> CONV2 --> CONV3 --> CONV4 --> CONV5 --> CONV6
    CONV6 -->|"Approve"| CONV7 --> CONV8 --> CONV9
    CONV6 -->|"Deny - proceed<br/>with preliminary"| CONV16

    CONV9 -->|"Approve"| CONV10 --> CONV11 --> CONV12 --> CONV13 --> CONV14 --> CONV15 --> CONV16

    style CONV1 fill:#27ae60,color:#fff
    style CONV4 fill:#16a085,color:#fff
    style CONV8 fill:#f39c12,color:#fff
    style CONV11 fill:#27ae60,color:#fff
    style CONV13 fill:#27ae60,color:#fff
    style CONV12 fill:#e74c3c,color:#fff
```

**Key Rule:** When converting from preliminary to detailed, the **same inspector** must be reassigned. The system enforces a "conversion lock" to prevent reassignment to a different inspector.

---

## 11. Media Source - Direct Lodge Flow

> Special shortcut flow for petitions sourced from Electronic & Print Media.

```mermaid
flowchart TD
    ML1["Petition Source: MEDIA<br/>(Electronic & Print Media)"]
    ML2["Normal flow until...<br/>Inspector submits report"]
    ML3["Status: ENQUIRY REPORT SUBMITTED"]
    ML4["CVO Reviews Report"]
    ML5{"CVO Decision"}

    ML6["CVO DIRECT LODGE<br/>- Provide Lodge Remarks<br/>- Skips PO entirely"]
    ML7["Status: LODGED"]
    ML8["Case can be closed"]

    ML9["Normal Forward to PO<br/>(if CVO prefers)"]

    ML1 --> ML2 --> ML3 --> ML4 --> ML5
    ML5 -->|"Direct Lodge<br/>(media shortcut)"| ML6 --> ML7 --> ML8
    ML5 -->|"Forward to PO<br/>(standard)"| ML9

    style ML1 fill:#3498db,color:#fff
    style ML3 fill:#16a085,color:#fff
    style ML6 fill:#e67e22,color:#fff
    style ML7 fill:#8e44ad,color:#fff
```

**Note:** This shortcut is ONLY available for petitions with `source_of_petition = 'Electronic & Print Media'`.

---

## 12. Beyond SLA Escalation Flow

> Special flow when a petition exceeds the 90-day SLA deadline.

```mermaid
flowchart TD
    SLA1["Petition exceeds 90-day SLA"]
    SLA2["System flags petition as overdue"]
    SLA3["PO initiates escalation"]
    SLA4["PO uses 'Beyond SLA Send to CVO'<br/>- Uploads permission copy"]
    SLA5["is_overdue_escalated = TRUE"]
    SLA6["Petition re-routed to CVO<br/>with escalation notation"]
    SLA7["Special tracking entry created"]
    SLA8["CVO handles with priority"]

    SLA1 --> SLA2 --> SLA3 --> SLA4 --> SLA5 --> SLA6 --> SLA7 --> SLA8

    style SLA1 fill:#e74c3c,color:#fff
    style SLA2 fill:#e74c3c,color:#fff
    style SLA5 fill:#f39c12,color:#fff
    style SLA8 fill:#e67e22,color:#fff
```

---

## 13. PO Direct Lodge (No Enquiry Needed)

> Flow when PO determines a petition does not require any field investigation.

```mermaid
flowchart TD
    DL1["Petition at Status:<br/>SENT FOR PERMISSION"]
    DL2["PO Reviews Petition"]
    DL3{"PO Determines<br/>No Enquiry Needed"}
    DL4["PO Selects 'Direct Lodge'<br/>- Provides Lodge Remarks"]
    DL5["Status: LODGED<br/>(bypasses entire enquiry cycle)"]
    DL6["PO Closes Petition"]
    DL7["Status: CLOSED"]

    DL1 --> DL2 --> DL3
    DL3 -->|"No enquiry<br/>required"| DL4 --> DL5 --> DL6 --> DL7
    DL3 -->|"Enquiry needed"| DL8["Normal approval flow"]

    style DL1 fill:#f39c12,color:#fff
    style DL5 fill:#8e44ad,color:#fff
    style DL7 fill:#2c3e50,color:#fff
```

---

## 14. Complete Status Transition Matrix

> Shows every status and which role can trigger transitions.

```mermaid
stateDiagram-v2
    [*] --> RECEIVED : DEO creates petition

    RECEIVED --> FORWARDED_TO_CVO : DEO forwards

    FORWARDED_TO_CVO --> ASSIGNED_TO_INSPECTOR : CVO (direct enquiry)
    FORWARDED_TO_CVO --> SENT_FOR_PERMISSION : CVO sends for permission

    SENT_FOR_PERMISSION --> PERMISSION_APPROVED : PO approves
    SENT_FOR_PERMISSION --> PERMISSION_REJECTED : PO rejects
    SENT_FOR_PERMISSION --> LODGED : PO direct lodge

    PERMISSION_APPROVED --> ASSIGNED_TO_INSPECTOR : CVO assigns inspector
    PERMISSION_REJECTED --> [*]

    ASSIGNED_TO_INSPECTOR --> ENQUIRY_REPORT_SUBMITTED : Inspector submits report
    ASSIGNED_TO_INSPECTOR --> SENT_BACK_REENQUIRY : CVO re-enquiry

    ENQUIRY_REPORT_SUBMITTED --> CVO_COMMENTS_ADDED : CVO adds comments
    ENQUIRY_REPORT_SUBMITTED --> FORWARDED_TO_PO : CVO forwards
    ENQUIRY_REPORT_SUBMITTED --> SENT_BACK_REENQUIRY : CVO re-enquiry
    ENQUIRY_REPORT_SUBMITTED --> LODGED : CVO direct lodge (media)
    ENQUIRY_REPORT_SUBMITTED --> SENT_FOR_PERMISSION : Conversion request

    SENT_BACK_REENQUIRY --> ENQUIRY_REPORT_SUBMITTED : Inspector resubmits

    CVO_COMMENTS_ADDED --> FORWARDED_TO_PO : CVO forwards

    FORWARDED_TO_PO --> CLOSED : PO conclusion
    FORWARDED_TO_PO --> ACTION_INSTRUCTED : PO instructs CMD
    FORWARDED_TO_PO --> LODGED : PO lodges
    FORWARDED_TO_PO --> SENT_BACK_REENQUIRY : PO re-enquiry

    ACTION_INSTRUCTED --> ACTION_TAKEN : CMD submits report

    ACTION_TAKEN --> LODGED : PO lodges
    ACTION_TAKEN --> CLOSED : PO conclusion

    LODGED --> CLOSED : PO closes

    CLOSED --> [*]
```

---

## 15. 6-Stage Workflow Summary

```mermaid
flowchart LR
    subgraph "STAGE 1<br/>Petition Initiated"
        S1A["RECEIVED"]
        S1B["FORWARDED TO CVO"]
        S1C["SENT FOR PERMISSION"]
        S1D["PERMISSION APPROVED"]
        S1E["PERMISSION REJECTED"]
    end

    subgraph "STAGE 2<br/>Enquiry In Progress"
        S2A["ASSIGNED TO INSPECTOR"]
        S2B["SENT BACK RE-ENQUIRY"]
    end

    subgraph "STAGE 3<br/>Report Finalized"
        S3A["ENQUIRY REPORT SUBMITTED"]
        S3B["CVO COMMENTS ADDED"]
        S3C["FORWARDED TO PO"]
    end

    subgraph "STAGE 4<br/>Action Pending"
        S4A["ACTION INSTRUCTED"]
        S4B["ACTION TAKEN"]
    end

    subgraph "STAGE 5<br/>Lodged"
        S5A["LODGED"]
    end

    subgraph "STAGE 6<br/>Closed"
        S6A["CLOSED"]
    end

    S1A --> S1B --> S1C --> S1D
    S1D --> S2A
    S2A --> S3A
    S3A --> S3B --> S3C
    S3C --> S4A --> S4B
    S4B --> S5A --> S6A

    style S1A fill:#3498db,color:#fff
    style S1B fill:#3498db,color:#fff
    style S1C fill:#3498db,color:#fff
    style S1D fill:#3498db,color:#fff
    style S1E fill:#e74c3c,color:#fff
    style S2A fill:#27ae60,color:#fff
    style S2B fill:#27ae60,color:#fff
    style S3A fill:#e67e22,color:#fff
    style S3B fill:#e67e22,color:#fff
    style S3C fill:#e67e22,color:#fff
    style S4A fill:#1abc9c,color:#fff
    style S4B fill:#1abc9c,color:#fff
    style S5A fill:#8e44ad,color:#fff
    style S6A fill:#2c3e50,color:#fff
```

---

## 16. SLA Timelines

```mermaid
gantt
    title Petition SLA Timelines by Case Type
    dateFormat  X
    axisFormat %d days

    section Preliminary Enquiry
    SLA Deadline :crit, 0, 15

    section Media Source Cases
    SLA Deadline :crit, 0, 45

    section Electrical Accident
    SLA Deadline :crit, 0, 45

    section Standard Detailed Enquiry
    SLA Deadline :crit, 0, 90
```

| Case Type | SLA Target | Escalation |
|---|---|---|
| Preliminary Enquiry | 15 days | Flagged as overdue |
| Media Source Cases | 45 days | Flagged as overdue |
| Electrical Accident | 45 days | Flagged as overdue |
| Standard Detailed Enquiry | 90 days | PO can escalate via "Beyond SLA" action |

---

## Quick Reference: Who Does What

| Role | Creates | Assigns | Investigates | Reviews | Approves | Acts | Closes |
|---|---|---|---|---|---|---|---|
| **Super Admin** | - | - | - | - | - | - | System Config |
| **DEO** | Yes | - | - | - | - | - | - |
| **CVO/DSP** | - | Yes | - | Yes | - | - | - |
| **Inspector** | - | - | Yes | - | - | - | - |
| **PO** | - | - | - | Yes | Yes | - | Yes |
| **CMD/CGM-HR** | - | - | - | - | - | Yes | - |

---

## Petition Types Handled

| # | Petition Type | Special Handling |
|---|---|---|
| 1 | Bribe | Standard flow |
| 2 | Corruption | Standard flow |
| 3 | Harassment | Standard flow |
| 4 | Electrical Accident | Extra accident detail fields in inspector report |
| 5 | Misconduct | Standard flow |
| 6 | Works Related | Standard flow |
| 7 | Irregularities in Tenders | Standard flow |
| 8 | Illegal Assets | Standard flow |
| 9 | Fake Certificates | Standard flow |
| 10 | Theft/Misappropriation of Materials | Standard flow |
| 11 | Other | Standard flow |

---

## Petition Sources

| # | Source | Special Rules |
|---|---|---|
| 1 | Electronic & Print Media | CVO can directly lodge after enquiry report |
| 2 | Public (Individual) | Standard flow |
| 3 | Government | Requires `govt_institution_type` selection |
| 4 | Sumoto | Standard flow |
| 5 | O/o CMD (Office of CMD) | Standard flow |

---

*Document generated for NIGAA Petition Tracker - AP TRANSCO Vigilance & Investigation System*
