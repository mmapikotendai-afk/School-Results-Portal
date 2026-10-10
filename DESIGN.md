---
name: Academic Register
description: A precise, contemporary records system shaped by the school crest and the rhythm of an academic register.
colors:
  crest-navy: "#001870"
  action-navy: "#001152"
  crest-red: "#a3000c"
  record-ink: "#1c2b31"
  secondary-ink: "#5a625e"
  paper: "#fbfbf9"
  rail: "#f0f1ec"
  rule: "#dfe2dc"
  success: "#08542e"
  warning: "#6e4700"
  danger: "#7a0b1e"
typography:
  display:
    fontFamily: "Newsreader, Georgia, Times New Roman, serif"
    fontSize: "2.125rem"
    fontWeight: 500
    lineHeight: 1.2
    letterSpacing: "-0.025em"
  title:
    fontFamily: "Public Sans Variable, system-ui, sans-serif"
    fontSize: "0.9375rem"
    fontWeight: 600
    lineHeight: 1.4
  body:
    fontFamily: "Public Sans Variable, system-ui, sans-serif"
    fontSize: "0.875rem"
    fontWeight: 400
    lineHeight: 1.6
  label:
    fontFamily: "Public Sans Variable, system-ui, sans-serif"
    fontSize: "0.75rem"
    fontWeight: 500
    lineHeight: 1.4
rounded:
  control: "6px"
  surface: "8px"
  compact: "3px"
spacing:
  xs: "4px"
  sm: "8px"
  md: "16px"
  lg: "28px"
  xl: "36px"
components:
  button-primary:
    backgroundColor: "{colors.action-navy}"
    textColor: "#ffffff"
    rounded: "{rounded.control}"
    padding: "10px 20px"
  button-secondary:
    backgroundColor: "#ffffff"
    textColor: "{colors.record-ink}"
    rounded: "{rounded.control}"
    padding: "10px 20px"
  input:
    backgroundColor: "#ffffff"
    textColor: "{colors.record-ink}"
    rounded: "{rounded.control}"
    height: "42px"
  card:
    backgroundColor: "#ffffff"
    textColor: "{colors.record-ink}"
    rounded: "{rounded.surface}"
    padding: "20px"
---

# Design System: Academic Register

## Overview

**Creative North Star: "The Living Academic Register"**

The portal takes the order and credibility of a formal school register and turns it into a calm digital workspace. The crest, measured rules, serif record headings, and tabular figures provide institutional character. Open white surfaces, a warm neutral rail, and compact controls keep the application contemporary and efficient.

The system is information dense without feeling compressed. Administration leads with the current term, work requiring attention, and publication readiness. Teaching screens lead with assigned subjects and unfinished marks. Student screens read as personal academic records, with identity and published results carrying more editorial weight.

**Key Characteristics:**

- Warm, quiet grounds with high-contrast ink.
- Crest navy for action and structure; crest red used sparingly as an institutional mark.
- Newsreader for record identity and page headings; Public Sans for operational content.
- Fine rules, modest corners, and flat surfaces at rest.
- Compact real data in place of decorative dashboard statistics.

## Colors

The palette is taken from the supplied crest and balanced with warm paper neutrals.

### Primary

- **Crest Navy:** Anchors active navigation, links, focus, and progress.
- **Action Navy:** Carries primary buttons and the strongest operational actions.

### Secondary

- **Crest Red:** Marks the active destination and small institutional details. It is not the error color.

### Tertiary

- **Success, Warning, and Danger:** Muted semantic inks and grounds communicate state while keeping the records readable in dense lists.

### Neutral

- **Record Ink:** Headings and primary record content.
- **Secondary Ink:** Supporting copy, labels, and metadata.
- **Paper:** The application canvas.
- **Rail:** The navigation and sign-in identity ground.
- **Rule:** Borders, dividers, and table structure.

### Named Rules

**The Crest Red Rule.** Use red as a rare school identity signal; reserve garnet danger colors for errors and overdue work.

**The Record Is the Color Rule.** Status color clarifies actual data; it does not decorate empty containers.

## Typography

**Display Font:** Newsreader (with Georgia and Times New Roman fallbacks)

**Body Font:** Public Sans Variable (with system UI fallbacks)

**Character:** Newsreader gives names, examinations, and page headings the authority of a formal record. Public Sans keeps forms, tables, navigation, and small metadata crisp.

### Hierarchy

- **Display** (500, 30–34px, 1.2): Page titles and important record identity.
- **Headline** (500, 24–28px, 1.2): Examination names and student names.
- **Title** (600, 15–16px, 1.4): Section and subject headings.
- **Body** (400, 14px, 1.6): Instructions, descriptions, and record content; prose stays near 68 characters per line.
- **Label** (500–600, 11–12px): Field labels, table headings, and metadata. Uppercase is limited to compact data labels and table columns.

### Named Rules

**The Two-Voice Rule.** Newsreader names the record; Public Sans operates it.

**The Numeral Rule.** Counts, dates, marks, and percentages use tabular numerals wherever columns must align.

## Layout

Authenticated screens use a 236px light navigation rail and a content area capped at 1320px. The rail collapses to 76px on desktop and becomes a native modal drawer below 1024px. Page spacing follows an 8px-based rhythm, with 28–36px separating major sections.

Administrative and teacher screens keep filters directly above their result sets. The admin workspace uses a main work column and a 280px action column on wide screens; the action column moves before long submission lists on narrow screens. Student records use the same structure with more editorial type and less operational chrome.

Tables become labelled record rows below 768px. No field is silently discarded. Long names wrap, action groups remain reachable, and modal actions stay fixed while their bodies scroll.

## Elevation & Depth

The interface is flat by default. White surfaces are separated from the paper ground by a single quiet border. The active navigation item uses a minimal ambient shadow; modal dialogs alone use substantial elevation because they occupy the browser top layer.

### Shadow Vocabulary

- **Active navigation:** `0 1px 3px rgb(22 35 32 / 0.08)` for the current destination only.
- **Modal overlay:** `0 24px 48px -12px rgb(0 0 0 / 0.28)` for focused, interruptive tasks.

### Named Rules

**The Flat Register Rule.** Borders and ground shifts establish hierarchy; shadows are reserved for state and top-layer dialogs.

## Shapes

Controls use gently squared 6px corners. Content surfaces stop at 8px, while compact chips and progress tracks use 3px. Circular shapes are limited to avatars, small status dots, and native spinner geometry. Hairline borders provide the recurring register structure.

## Components

### Buttons

- **Shape:** Compact 6px corners and a minimum 36px height for small controls.
- **Primary:** Deep action navy, white text, and semibold labels.
- **Hover / Focus:** A darker or lighter navy state plus a 2px external navy focus outline.
- **Secondary / Ghost:** White bordered controls for parallel actions; unbordered ink controls for low-priority actions.

### Chips

- **Style:** Small, squared status fields with a tinted ground and semantic ink. Text always names the state, so meaning never relies on color.
- **State:** Filter tabs use the same compact geometry and expose pressed state to assistive technology.

### Cards / Containers

- **Corner Style:** Modest surface corners (8px).
- **Background:** White on a warm paper ground.
- **Shadow Strategy:** Flat at rest.
- **Border:** One quiet rule around a grouped record.
- **Internal Padding:** 20–24px on wide screens and 16–20px on phones.

### Inputs / Fields

- **Style:** White field, quiet neutral border, 6px corners, and a 42px default height.
- **Focus:** Navy border and a consistent external 2px focus outline.
- **Error / Disabled:** Garnet border and text for errors; warm neutral ground and subdued text when disabled.

### Navigation

The light rail groups destinations by school workflow. The active item is white with navy ink, a tiny crest-red dot, and a restrained shadow. The collapsed rail retains real icons, labels through accessible names and browser titles, and a dedicated expand control. Mobile navigation uses a native dialog for focus trapping and Escape behavior.

### Record Census

The admin census is a border-led inline register, not a row of equal metric cards. Each real total links to its underlying record and wraps cleanly on phones.

## Do's and Don'ts

### Do:

- **Do** lead each role with its current task and authorised data.
- **Do** keep filters beside the table or register they affect.
- **Do** pair every status color with direct text.
- **Do** let student names and examination titles wrap without truncating the record itself.
- **Do** use the supplied crest and configured school identity.

### Don't:

- **Don't** create oversized, repeated KPI cards or decorative charts.
- **Don't** add gradients, glass effects, giant corners, or floating translucent panels.
- **Don't** use the crest red for routine errors or every primary action.
- **Don't** invent enrolment states, performance data, activity, or school claims.
- **Don't** hide record fields on mobile merely to make a table fit.
