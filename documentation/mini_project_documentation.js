const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
  AlignmentType, LevelFormat, BorderStyle, WidthType, ShadingType, PageBreak,
  TabStopType, TabStopPosition, HeadingLevel
} = require('docx');
const fs = require('fs');
const path = require('path');

// ─── FONT & SIZE CONSTANTS ──────────────────────────────────────────────────
const F = "Bookman Old Style";
const SZ = { content: 24, title: 28, chapter: 32 }; // 12pt, 14pt, 16pt (half-points)
const LS = { line: 276, lineRule: "auto" };         // 1.15 line spacing
const AP = 180;                                     // after-paragraph spacing

// ─── HELPER BUILDERS ────────────────────────────────────────────────────────
const cp = (text) => new Paragraph({
  children: [new TextRun({ text, font: F, size: SZ.content })],
  spacing: { after: AP, ...LS },
  alignment: AlignmentType.JUSTIFIED,
});
const cpBold = (text) => new Paragraph({
  children: [new TextRun({ text, font: F, size: SZ.content, bold: true })],
  spacing: { after: AP, ...LS },
  alignment: AlignmentType.JUSTIFIED,
});
const chHd = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_1,
  children: [new TextRun({ text, font: F, size: SZ.chapter, bold: true })],
  spacing: { before: 200, after: 400 },
  alignment: AlignmentType.CENTER,
});
const secHd = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_2,
  children: [new TextRun({ text, font: F, size: SZ.title, bold: true })],
  spacing: { before: 320, after: 160 },
});
const subHd = (text) => new Paragraph({
  heading: HeadingLevel.HEADING_3,
  children: [new TextRun({ text, font: F, size: SZ.content, bold: true })],
  spacing: { before: 200, after: 100 },
});
const pb = () => new Paragraph({ children: [new PageBreak()], spacing: { after: 0 } });
const ctr = (text, opts = {}) => new Paragraph({
  children: [new TextRun({ text, font: F, size: opts.size || SZ.content, bold: !!opts.bold, italics: !!opts.italic })],
  spacing: { after: opts.after !== undefined ? opts.after : 200 },
  alignment: AlignmentType.CENTER,
});
const el = () => new Paragraph({
  children: [new TextRun({ text: "", font: F, size: SZ.content })],
  spacing: { after: 100 },
});

// ─── TABLE HELPERS ──────────────────────────────────────────────────────────
const bdr = { style: BorderStyle.SINGLE, size: 1, color: "000000" };
const bdrs = { top: bdr, bottom: bdr, left: bdr, right: bdr };
const margs = { top: 80, bottom: 80, left: 120, right: 120 };

const tc = (text, isHdr, w, align) => new TableCell({
  borders: bdrs,
  width: { size: w, type: WidthType.DXA },
  margins: margs,
  shading: isHdr ? { fill: "CCCCCC", type: ShadingType.CLEAR } : undefined,
  children: [new Paragraph({
    children: [new TextRun({ text, font: F, size: SZ.content, bold: isHdr })],
    alignment: align || (isHdr ? AlignmentType.CENTER : AlignmentType.LEFT),
    spacing: { after: 0 },
  })],
});
const tcC = (text, isHdr, w) => tc(text, isHdr, w, AlignmentType.CENTER);

// ─── IMAGE HELPER ───────────────────────────────────────────────────────────
const diagramDir = path.join(__dirname, "diagrams");

function loadDiagram(filename, widthPx, heightPx, title, figNum) {
  const filePath = path.join(diagramDir, filename);
  const children = [];
  if (fs.existsSync(filePath)) {
    children.push(new Paragraph({
      children: [new ImageRun({
        type: "png",
        data: fs.readFileSync(filePath),
        transformation: { width: widthPx, height: heightPx },
        altText: { title: title, description: title, name: filename },
      })],
      spacing: { before: 200, after: 120 },
      alignment: AlignmentType.CENTER,
    }));
  } else {
    children.push(cp(`[Figure ${figNum}: ${title} — Image file not found: ${filename}]`));
  }
  children.push(ctr(`Figure ${figNum}: ${title}`, { size: 22, italic: true, after: 300 }));
  return children;
}

// ─── NUMBERING CONFIG ───────────────────────────────────────────────────────
const numbering = {
  config: [
    {
      reference: "bullets",
      levels: [{
        level: 0, format: LevelFormat.BULLET, text: "\u2022",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    },
    {
      reference: "numbers",
      levels: [{
        level: 0, format: LevelFormat.DECIMAL, text: "%1.",
        alignment: AlignmentType.LEFT,
        style: { paragraph: { indent: { left: 720, hanging: 360 } } }
      }]
    }
  ]
};

const bl = (text) => new Paragraph({
  numbering: { reference: "bullets", level: 0 },
  children: [new TextRun({ text, font: F, size: SZ.content })],
  spacing: { after: 100, ...LS },
});
const nl = (text) => new Paragraph({
  numbering: { reference: "numbers", level: 0 },
  children: [new TextRun({ text, font: F, size: SZ.content })],
  spacing: { after: 100, ...LS },
});

// ─── DOCUMENT STYLES ────────────────────────────────────────────────────────
const styles = {
  default: { document: { run: { font: F, size: SZ.content } } },
  paragraphStyles: [
    {
      id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: SZ.chapter, bold: true, font: F },
      paragraph: { spacing: { before: 200, after: 400 }, outlineLevel: 0 }
    },
    {
      id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: SZ.title, bold: true, font: F },
      paragraph: { spacing: { before: 320, after: 160 }, outlineLevel: 1 }
    },
    {
      id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
      run: { size: SZ.content, bold: true, font: F },
      paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 }
    },
  ]
};

// ─── PAGE PROPERTIES ────────────────────────────────────────────────────────
const pageProps = {
  page: {
    size: { width: 11906, height: 16838 }, // A4
    margin: { top: 1440, right: 1260, bottom: 1440, left: 1800 }
  }
};
// Content width = 11906 - 1800 - 1260 = 8846 DXA
const CW = 8846;

// ════════════════════════════════════════════════════════════════════════════
//   BUILD SECTIONS
// ════════════════════════════════════════════════════════════════════════════

// ── PRELIMINARY PAGES ───────────────────────────────────────────────────────
const preliminary = [
  // TITLE PAGE
  el(), el(), el(), el(),
  ctr("MARRI LAXMAN REDDY INSTITUTE OF TECHNOLOGY AND MANAGEMENT", { size: 28, bold: true, after: 100 }),
  ctr("Dundigal, Hyderabad – 500 043, Telangana, India", { size: 24, after: 100 }),
  ctr("Department of Computer Science and Engineering", { size: 26, bold: true, after: 400 }),
  ctr("M. Tech in Computer Science and Engineering", { size: 24, italic: true, after: 600 }),
  ctr("A Mini Project Report Submitted in Partial Fulfillment of the Requirements", { size: 24, after: 80 }),
  ctr("for the Award of the Degree of", { size: 24, after: 80 }),
  ctr("Master of Technology", { size: 26, bold: true, after: 600 }),
  ctr("EXPLAINABLE MULTI-AGENT HIERARCHICAL REINFORCEMENT", { size: 28, bold: true, after: 80 }),
  ctr("LEARNING FOR COOPERATIVE SEARCH AND RESCUE", { size: 28, bold: true, after: 80 }),
  ctr("IN DYNAMIC GRIDS", { size: 28, bold: true, after: 600 }),
  ctr("Submitted by", { size: 24, after: 80 }),
  ctr("SRINIVAS RAO TAMMIREDDY", { size: 26, bold: true, after: 80 }),
  ctr("Roll No: 23R21A0501", { size: 24, after: 500 }),
  ctr("Under the Guidance of", { size: 24, after: 80 }),
  ctr("Dr. S. Pratap Singh", { size: 26, bold: true, after: 80 }),
  ctr("Professor, Department of Computer Science and Engineering", { size: 24, after: 500 }),
  ctr("Academic Year: 2024-2025", { size: 24, after: 100 }),
  pb(),

  // DECLARATION
  chHd("DECLARATION"),
  el(),
  cp("I, Srinivas Rao Tammireddy, Roll No. 23R21A0501, pursuing M.Tech in Computer Science and Engineering at Marri Laxman Reddy Institute of Technology and Management, Dundigal, Hyderabad, hereby declare that the mini project report titled \"Explainable Multi-Agent Hierarchical Reinforcement Learning for Cooperative Search and Rescue in Dynamic Grids\" submitted in partial fulfillment of the requirements for the award of the degree of Master of Technology is a record of my original work carried out under the supervision of Dr. S. Pratap Singh, Professor, Department of Computer Science and Engineering."),
  cp("I further declare that this project report has not been submitted elsewhere, in part or in full, for the award of any other degree or diploma in any university or institution. All sources of information and references used in this work have been duly acknowledged."),
  cp("The work presented in this project report is genuine, original, and has been completed under the academic and research guidance provided by the faculty of the Department of Computer Science and Engineering."),
  el(), el(), el(),
  new Paragraph({
    children: [new TextRun({ text: "Place: Hyderabad", font: F, size: SZ.content })],
    spacing: { after: 100 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Date: _______________", font: F, size: SZ.content })],
    spacing: { after: 400 },
  }),
  ctr("(Srinivas Rao Tammireddy)"),
  pb(),

  // CERTIFICATE
  chHd("CERTIFICATE"),
  el(),
  cp("This is to certify that the mini project report titled \"Explainable Multi-Agent Hierarchical Reinforcement Learning for Cooperative Search and Rescue in Dynamic Grids\" submitted by Srinivas Rao Tammireddy (Roll No: 23R21A0501) in partial fulfillment of the requirements for the award of the degree of Master of Technology in Computer Science and Engineering at Marri Laxman Reddy Institute of Technology and Management, Dundigal, Hyderabad, is a record of original and independent work carried out by the candidate under my supervision and guidance."),
  cp("To the best of my knowledge, the work presented in this project report is genuine and original. No part of this report has been submitted previously for the award of any other degree or diploma in any university or institution."),
  cp("I recommend this project report to be placed before the examination committee for evaluation and approval."),
  el(), el(), el(),
  new Paragraph({
    children: [new TextRun({ text: "Place: Hyderabad", font: F, size: SZ.content })],
    spacing: { after: 100 },
  }),
  new Paragraph({
    children: [new TextRun({ text: "Date: _______________", font: F, size: SZ.content })],
    spacing: { after: 400 },
  }),
  new Paragraph({
    children: [
      new TextRun({ text: "Dr. S. Pratap Singh", font: F, size: SZ.content, bold: true }),
    ],
    spacing: { after: 80 },
  }),
  cp("Professor and Project Supervisor"),
  cp("Department of Computer Science and Engineering"),
  cp("Marri Laxman Reddy Institute of Technology and Management"),
  cp("Dundigal, Hyderabad – 500 043"),
  el(), el(),
  cpBold("Head of Department"),
  cp("Department of Computer Science and Engineering"),
  cp("Marri Laxman Reddy Institute of Technology and Management"),
  pb(),

  // ACKNOWLEDGMENT
  chHd("ACKNOWLEDGMENT"),
  el(),
  cp("I express my deepest sense of gratitude and sincere thanks to Dr. S. Pratap Singh, Professor, Department of Computer Science and Engineering, Marri Laxman Reddy Institute of Technology and Management, for his invaluable guidance, constant encouragement, and meticulous supervision throughout the course of this project work. His deep expertise in artificial intelligence and reinforcement learning has been an immense source of inspiration and motivation."),
  cp("I extend my heartfelt gratitude to the Head of the Department of Computer Science and Engineering and the entire faculty staff for providing the necessary academic environment and computational resources throughout my M.Tech program."),
  cp("I am profoundly thankful to the Principal and Management of Marri Laxman Reddy Institute of Technology and Management for providing the infrastructure and a conducive learning environment that made this project possible."),
  cp("I also wish to acknowledge the researchers and authors of the numerous scholarly articles and conference proceedings that have formed the theoretical foundations of this work."),
  cp("Special thanks are due to my colleagues and peers for their stimulating discussions and moral encouragement during challenging phases of this project."),
  cp("Finally, I owe an immeasurable debt of gratitude to my family for their unwavering love, patience, and encouragement."),
  el(), el(),
  new Paragraph({
    children: [new TextRun({ text: "Srinivas Rao Tammireddy", font: F, size: SZ.content })],
    spacing: { after: 100 },
    alignment: AlignmentType.RIGHT,
  }),
  pb(),

  // ABSTRACT
  chHd("ABSTRACT"),
  el(),
  cp("Search and rescue (SAR) operations in disaster-stricken environments present demanding challenges for autonomous multi-agent systems. The dynamic and partially observable nature of disaster grids — characterized by spreading fire hazards, blocked pathways, and time-critical victim location requirements — demands coordination mechanisms that are efficient, adaptive, and interpretable by human rescue coordinators."),
  cp("This project presents an Explainable Multi-Agent Hierarchical Reinforcement Learning (EMARL-SAR) framework for cooperative search and rescue operations in dynamic grid environments. The framework deploys three heterogeneous agents — two reconnaissance drones and one path-clearing rescue rover — within a 15×15 dynamic grid representing a disaster zone. Agents learn cooperative rescue strategies through a two-level hierarchical policy architecture: the high-level policy uses a Q-table with epsilon-greedy selection to assign strategic macro-goals (quadrant assignments, charge station routing, or victim/debris targeting), while the low-level policy employs a Deep Q-Network (DQN) with a 64-64 MLP architecture combined with a BFS pathfinder for step-by-step primitive navigation actions."),
  cp("A dedicated Explainability Engine is integrated throughout the framework, providing real-time justifications of all agent decisions. The engine generates high-level sector assignment rationales, low-level spatial movement justifications, and gradient-based saliency attributions that decompose each decision into interpretable feature contributions (target proximity, battery status, and hazard avoidance)."),
  cp("The EMARL-SAR framework is implemented in Python using PyTorch for DQN training, a custom grid environment, and an HTTP server with a live HTML dashboard for real-time visualization. Experimental evaluation demonstrates that the hierarchical approach achieves consistent victim rescue, with coordination efficiency improvements compared to flat single-policy baselines."),
  el(),
  cpBold("Keywords: Search and Rescue, Multi-Agent Reinforcement Learning, Hierarchical Reinforcement Learning, Explainable AI, Dynamic Grid Environment, Cooperative Coordination, Decision Traceability"),
  pb(),

  // TABLE OF CONTENTS
  chHd("TABLE OF CONTENTS"),
  el(),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [CW - 1200, 1200],
    rows: [
      new TableRow({ children: [tc("TITLE", true, CW - 1200), tcC("PAGE NO.", true, 1200)] }),
      new TableRow({ children: [tc("Declaration", false, CW - 1200), tcC("ii", false, 1200)] }),
      new TableRow({ children: [tc("Certificate", false, CW - 1200), tcC("iii", false, 1200)] }),
      new TableRow({ children: [tc("Acknowledgment", false, CW - 1200), tcC("iv", false, 1200)] }),
      new TableRow({ children: [tc("Abstract", false, CW - 1200), tcC("v", false, 1200)] }),
      new TableRow({ children: [tc("Table of Contents", false, CW - 1200), tcC("vi", false, 1200)] }),
      new TableRow({ children: [tc("List of Figures", false, CW - 1200), tcC("viii", false, 1200)] }),
      new TableRow({ children: [tc("List of Tables", false, CW - 1200), tcC("ix", false, 1200)] }),
      new TableRow({ children: [tc("List of Abbreviations", false, CW - 1200), tcC("x", false, 1200)] }),
      new TableRow({ children: [tc("CHAPTER 1: INTRODUCTION", true, CW - 1200), tcC("1", true, 1200)] }),
      new TableRow({ children: [tc("1.1  Introduction", false, CW - 1200), tcC("1", false, 1200)] }),
      new TableRow({ children: [tc("1.2  Background of the Problem", false, CW - 1200), tcC("2", false, 1200)] }),
      new TableRow({ children: [tc("1.3  Motivation", false, CW - 1200), tcC("3", false, 1200)] }),
      new TableRow({ children: [tc("1.4  Problem Statement", false, CW - 1200), tcC("4", false, 1200)] }),
      new TableRow({ children: [tc("1.5  Proposed Solution", false, CW - 1200), tcC("5", false, 1200)] }),
      new TableRow({ children: [tc("1.6  Objectives", false, CW - 1200), tcC("6", false, 1200)] }),
      new TableRow({ children: [tc("1.7  Scope of the Work", false, CW - 1200), tcC("7", false, 1200)] }),
      new TableRow({ children: [tc("1.8  Research Methodology", false, CW - 1200), tcC("8", false, 1200)] }),
      new TableRow({ children: [tc("1.9  Organization of the Report", false, CW - 1200), tcC("9", false, 1200)] }),
      new TableRow({ children: [tc("1.10 Summary", false, CW - 1200), tcC("10", false, 1200)] }),
      new TableRow({ children: [tc("CHAPTER 2: LITERATURE SURVEY", true, CW - 1200), tcC("11", true, 1200)] }),
      new TableRow({ children: [tc("2.1  Introduction", false, CW - 1200), tcC("11", false, 1200)] }),
      new TableRow({ children: [tc("2.2  Existing Systems", false, CW - 1200), tcC("11", false, 1200)] }),
      new TableRow({ children: [tc("2.3  Research Papers Review", false, CW - 1200), tcC("13", false, 1200)] }),
      new TableRow({ children: [tc("2.4  Comparative Study", false, CW - 1200), tcC("18", false, 1200)] }),
      new TableRow({ children: [tc("2.5  Research Gap", false, CW - 1200), tcC("20", false, 1200)] }),
      new TableRow({ children: [tc("2.6  Summary", false, CW - 1200), tcC("21", false, 1200)] }),
      new TableRow({ children: [tc("CHAPTER 3: PROPOSED METHODOLOGY", true, CW - 1200), tcC("22", true, 1200)] }),
      new TableRow({ children: [tc("3.1  Introduction", false, CW - 1200), tcC("22", false, 1200)] }),
      new TableRow({ children: [tc("3.2  Proposed System", false, CW - 1200), tcC("22", false, 1200)] }),
      new TableRow({ children: [tc("3.3  Working Principle", false, CW - 1200), tcC("24", false, 1200)] }),
      new TableRow({ children: [tc("3.4  Proposed System Architecture", false, CW - 1200), tcC("26", false, 1200)] }),
      new TableRow({ children: [tc("3.5  Module Descriptions", false, CW - 1200), tcC("28", false, 1200)] }),
      new TableRow({ children: [tc("3.6  System Design", false, CW - 1200), tcC("33", false, 1200)] }),
      new TableRow({ children: [tc("3.7  Mathematical Model", false, CW - 1200), tcC("35", false, 1200)] }),
      new TableRow({ children: [tc("3.8  Technologies Used", false, CW - 1200), tcC("37", false, 1200)] }),
      new TableRow({ children: [tc("3.9  Hardware and Software Requirements", false, CW - 1200), tcC("38", false, 1200)] }),
      new TableRow({ children: [tc("3.10 Summary", false, CW - 1200), tcC("39", false, 1200)] }),
      new TableRow({ children: [tc("CHAPTER 4: IMPLEMENTATION AND RESULTS", true, CW - 1200), tcC("40", true, 1200)] }),
      new TableRow({ children: [tc("4.1  Introduction", false, CW - 1200), tcC("40", false, 1200)] }),
      new TableRow({ children: [tc("4.2  Experimental Setup", false, CW - 1200), tcC("40", false, 1200)] }),
      new TableRow({ children: [tc("4.3  Implementation Details", false, CW - 1200), tcC("42", false, 1200)] }),
      new TableRow({ children: [tc("4.4  Experimental Screenshots", false, CW - 1200), tcC("44", false, 1200)] }),
      new TableRow({ children: [tc("4.5  Performance Evaluation", false, CW - 1200), tcC("45", false, 1200)] }),
      new TableRow({ children: [tc("4.6  Discussion of Results", false, CW - 1200), tcC("47", false, 1200)] }),
      new TableRow({ children: [tc("4.7  Summary", false, CW - 1200), tcC("48", false, 1200)] }),
      new TableRow({ children: [tc("CHAPTER 5: CONCLUSION AND FUTURE WORK", true, CW - 1200), tcC("49", true, 1200)] }),
      new TableRow({ children: [tc("5.1  Conclusion", false, CW - 1200), tcC("49", false, 1200)] }),
      new TableRow({ children: [tc("5.2  Contributions", false, CW - 1200), tcC("50", false, 1200)] }),
      new TableRow({ children: [tc("5.3  Limitations", false, CW - 1200), tcC("51", false, 1200)] }),
      new TableRow({ children: [tc("5.4  Future Scope", false, CW - 1200), tcC("52", false, 1200)] }),
      new TableRow({ children: [tc("5.5  Summary", false, CW - 1200), tcC("53", false, 1200)] }),
      new TableRow({ children: [tc("REFERENCES", true, CW - 1200), tcC("54", true, 1200)] }),
    ]
  }),
  pb(),

  // LIST OF FIGURES
  chHd("LIST OF FIGURES"),
  el(),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [1000, CW - 2200, 1200],
    rows: [
      new TableRow({ children: [tcC("Fig. No.", true, 1000), tc("Title of Figure", true, CW - 2200), tcC("Page No.", true, 1200)] }),
      new TableRow({ children: [tcC("3.1", false, 1000), tc("Overall Architecture of the EMARL-SAR Framework", false, CW - 2200), tcC("27", false, 1200)] }),
      new TableRow({ children: [tcC("3.2", false, 1000), tc("Two-Level Hierarchical Policy Structure", false, CW - 2200), tcC("29", false, 1200)] }),
      new TableRow({ children: [tcC("3.3", false, 1000), tc("Explainability Engine Workflow", false, CW - 2200), tcC("32", false, 1200)] }),
      new TableRow({ children: [tcC("3.4", false, 1000), tc("SMDP Training Loop", false, CW - 2200), tcC("34", false, 1200)] }),
      new TableRow({ children: [tcC("3.5", false, 1000), tc("Environment State Diagram", false, CW - 2200), tcC("35", false, 1200)] }),
      new TableRow({ children: [tcC("3.6", false, 1000), tc("Agent Decision and Navigation Flow", false, CW - 2200), tcC("36", false, 1200)] }),
    ]
  }),
  pb(),

  // LIST OF TABLES
  chHd("LIST OF TABLES"),
  el(),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [1200, CW - 2400, 1200],
    rows: [
      new TableRow({ children: [tcC("Table No.", true, 1200), tc("Title of Table", true, CW - 2400), tcC("Page No.", true, 1200)] }),
      new TableRow({ children: [tcC("2.1", false, 1200), tc("Comparative Study of Existing MARL and HRL Methods", false, CW - 2400), tcC("18", false, 1200)] }),
      new TableRow({ children: [tcC("3.1", false, 1200), tc("Software Requirements", false, CW - 2400), tcC("38", false, 1200)] }),
      new TableRow({ children: [tcC("3.2", false, 1200), tc("Hardware Requirements", false, CW - 2400), tcC("38", false, 1200)] }),
      new TableRow({ children: [tcC("4.1", false, 1200), tc("Hyperparameter Configuration", false, CW - 2400), tcC("41", false, 1200)] }),
      new TableRow({ children: [tcC("4.2", false, 1200), tc("Environment Configuration Parameters", false, CW - 2400), tcC("41", false, 1200)] }),
      new TableRow({ children: [tcC("4.3", false, 1200), tc("Performance Metrics Comparison", false, CW - 2400), tcC("46", false, 1200)] }),
    ]
  }),
  pb(),

  // LIST OF ABBREVIATIONS
  chHd("LIST OF ABBREVIATIONS"),
  el(),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [2200, CW - 2200],
    rows: [
      new TableRow({ children: [tcC("Abbreviation", true, 2200), tc("Full Form", true, CW - 2200)] }),
      new TableRow({ children: [tcC("AI", false, 2200), tc("Artificial Intelligence", false, CW - 2200)] }),
      new TableRow({ children: [tcC("SAR", false, 2200), tc("Search and Rescue", false, CW - 2200)] }),
      new TableRow({ children: [tcC("MARL", false, 2200), tc("Multi-Agent Reinforcement Learning", false, CW - 2200)] }),
      new TableRow({ children: [tcC("HRL", false, 2200), tc("Hierarchical Reinforcement Learning", false, CW - 2200)] }),
      new TableRow({ children: [tcC("XAI", false, 2200), tc("Explainable Artificial Intelligence", false, CW - 2200)] }),
      new TableRow({ children: [tcC("EMARL-SAR", false, 2200), tc("Explainable Multi-Agent RL for Search and Rescue", false, CW - 2200)] }),
      new TableRow({ children: [tcC("RL", false, 2200), tc("Reinforcement Learning", false, CW - 2200)] }),
      new TableRow({ children: [tcC("DQN", false, 2200), tc("Deep Q-Network", false, CW - 2200)] }),
      new TableRow({ children: [tcC("MDP", false, 2200), tc("Markov Decision Process", false, CW - 2200)] }),
      new TableRow({ children: [tcC("SMDP", false, 2200), tc("Semi-Markov Decision Process", false, CW - 2200)] }),
      new TableRow({ children: [tcC("BFS", false, 2200), tc("Breadth-First Search", false, CW - 2200)] }),
      new TableRow({ children: [tcC("FOV", false, 2200), tc("Field of View", false, CW - 2200)] }),
      new TableRow({ children: [tcC("SSE", false, 2200), tc("Server-Sent Events", false, CW - 2200)] }),
      new TableRow({ children: [tcC("UAV", false, 2200), tc("Unmanned Aerial Vehicle", false, CW - 2200)] }),
    ]
  }),
  pb(),
];

// ════════════════════════════════════════════════════════════════════════════
//  CHAPTER 1: INTRODUCTION
// ════════════════════════════════════════════════════════════════════════════
const ch1 = [
  chHd("CHAPTER 1: INTRODUCTION"),

  secHd("1.1 Introduction"),
  cp("Search and rescue (SAR) operations in disaster-stricken environments constitute one of the most time-critical and operationally demanding applications of autonomous multi-agent systems. Natural disasters such as earthquakes, building collapses, and industrial fires create environments that are inherently dangerous for human responders, partially observable due to structural damage, and dynamically evolving as hazards spread over time. The deployment of autonomous agents — unmanned aerial vehicles (UAVs) for reconnaissance and ground robots for physical rescue — has emerged as a promising approach to augment human SAR capabilities while minimizing risk to human responders."),
  cp("Multi-agent reinforcement learning (MARL) provides a principled framework for enabling autonomous agents to learn cooperative strategies through interaction with the environment. However, standard flat MARL approaches face fundamental scalability challenges in SAR scenarios due to the combinatorial explosion of the joint action space as the number of agents increases. Hierarchical reinforcement learning (HRL) addresses this challenge by decomposing the decision-making process into multiple levels of temporal abstraction, enabling agents to reason about strategic objectives separately from low-level navigation actions."),
  cp("A critical barrier to the deployment of autonomous SAR systems is the lack of decision transparency. Human rescue coordinators require an understanding of why autonomous agents select specific actions in order to maintain situational awareness, override erroneous decisions, and establish trust in the system. Explainable AI (XAI) techniques provide mechanisms for generating human-comprehensible justifications of agent decisions, addressing the transparency requirements of safety-critical autonomous systems."),
  cp("This project presents an Explainable Multi-Agent Hierarchical Reinforcement Learning (EMARL-SAR) framework that integrates hierarchical policy learning with a real-time explainability engine for cooperative SAR coordination in dynamic grid environments."),

  secHd("1.2 Background of the Problem"),
  cp("Traditional SAR coordination relies on centralised human command and control, where rescue coordinators manually assign search sectors, monitor agent progress, and adjust plans in response to evolving conditions. This approach is inherently limited by human cognitive bandwidth — a single coordinator cannot effectively manage more than 2-3 autonomous agents simultaneously while processing dynamic environmental information."),
  cp("Reinforcement learning has demonstrated remarkable success in learning complex decision-making strategies through trial-and-error interaction with simulated environments. However, applying standard RL to multi-agent SAR coordination presents three fundamental challenges. First, the joint action space grows exponentially with the number of agents, making flat policy learning computationally intractable for large agent teams. Second, the credit assignment problem — determining which agent actions contributed to team success or failure — becomes significantly more complex in cooperative multi-agent settings. Third, the learned policies operate as opaque neural network models that provide no insight into the reasoning behind individual agent decisions."),

  secHd("1.3 Motivation"),
  cp("The motivation for this project stems from the convergence of three research needs. First, there is a well-documented requirement for coordination mechanisms that can scale multi-agent SAR operations beyond the cognitive limits of human coordinators. Second, the hierarchical decomposition of SAR decision-making — separating strategic sector assignment from tactical navigation — aligns naturally with the operational structure of real-world SAR operations. Third, regulatory and operational requirements for autonomous systems in safety-critical domains demand decision transparency that current black-box MARL approaches cannot provide."),
  cp("The specific motivation for developing the EMARL-SAR framework arises from the observation that existing MARL approaches for SAR coordination treat the coordination problem as a monolithic flat policy learning task, ignoring the natural hierarchical structure of SAR operations. By explicitly decomposing the coordination problem into macro-goal assignment and micro-action execution, the framework can achieve more efficient learning while simultaneously enabling explanations at multiple levels of abstraction."),

  secHd("1.4 Problem Statement"),
  cp("The problem addressed in this project is defined as follows: Given a dynamic grid environment containing multiple victims, obstacles (debris), and time-evolving hazards (spreading fire), design and implement a multi-agent coordination framework that enables heterogeneous autonomous agents (reconnaissance drones and rescue rovers) to cooperatively locate and rescue all victims while avoiding hazards, managing energy resources, and providing real-time human-interpretable explanations of all agent decisions."),
  cp("The problem encompasses three sub-challenges: (1) efficient hierarchical policy learning for multi-agent coordination under partial observability and dynamic hazards, (2) integration of real-time explainability mechanisms within the hierarchical decision-making pipeline, and (3) development of a live visualization dashboard for monitoring agent operations and explanation outputs."),

  secHd("1.5 Proposed Solution"),
  cp("The proposed solution is the EMARL-SAR framework, a three-component system comprising: (1) a two-level hierarchical reinforcement learning architecture with a Q-table high-level policy for macro-goal assignment and a DQN low-level policy with BFS pathfinding for primitive action execution, (2) an Explainability Engine that generates high-level sector assignment justifications, low-level spatial movement explanations, and gradient-based saliency attributions for each agent decision, and (3) a live HTTP-based dashboard that visualises the grid environment, agent trajectories, and explanation outputs in real time."),
  cp("The framework deploys three heterogeneous agents — two reconnaissance drones (A1, A2) with the ability to fly over debris but vulnerability to fire, and one rescue rover (A3) capable of clearing debris and rescuing victims — within a 15×15 dynamic grid. The high-level policy operates on a discretised state space (battery level, exploration progress, coordination status) and selects from a macro-goal space including quadrant centers, charge stations, and nearest victims or debris. The low-level policy uses a 12-dimensional state vector (relative sub-goal direction, battery level, 3×3 local surroundings) and selects primitive actions (North, South, East, West, Interact) using a DQN with BFS-guided navigation."),

  secHd("1.6 Objectives"),
  cp("The objectives of this project are:"),
  nl("To design and implement a two-level hierarchical reinforcement learning framework for cooperative multi-agent search and rescue in a dynamic grid environment."),
  nl("To integrate a real-time Explainability Engine that generates human-interpretable justifications and gradient-based saliency attributions for all agent decisions."),
  nl("To evaluate the framework performance through rescue success metrics and comparative analysis against non-hierarchical baselines."),

  secHd("1.7 Scope of the Work"),
  cp("The scope of this project encompasses the design, implementation, and experimental evaluation of the EMARL-SAR framework within a simulated 15×15 dynamic grid environment. The framework supports a team of 3 heterogeneous agents (2 drones and 1 rover) coordinating to rescue 3 victims while navigating around 10 debris obstacles and 2 fire sources with stochastic spread mechanics. The implementation uses Python with PyTorch for DQN training, a custom grid environment class, and an HTTP server with a browser-based HTML dashboard for real-time simulation visualization."),
  cp("The project does not include physical robot deployment, integration with real-world sensor data, or evaluation with professional SAR operators. These extensions are identified as future work directions."),

  secHd("1.8 Research Methodology"),
  cp("The research methodology follows a systematic experimental approach comprising four phases. In the first phase, a comprehensive literature survey is conducted to identify existing approaches, research gaps, and relevant techniques in multi-agent RL, hierarchical RL, and explainable AI for autonomous systems. In the second phase, the EMARL-SAR framework is designed and implemented, including the environment simulator, hierarchical policy architecture, explainability engine, and visualization dashboard. In the third phase, the framework is trained using the SMDP-based hierarchical training loop and evaluated across performance metrics. In the fourth phase, the results are analyzed, compared against baselines, and conclusions are drawn."),

  secHd("1.9 Organization of the Report"),
  cp("This report is organized into five chapters. Chapter 1 introduces the problem domain, motivation, objectives, and proposed solution. Chapter 2 presents a literature survey of related work in multi-agent RL, hierarchical RL, and explainable AI. Chapter 3 describes the proposed methodology, system architecture, module designs, and mathematical formulation. Chapter 4 details the implementation, experimental setup, and results analysis. Chapter 5 concludes with contributions, limitations, and future work directions."),

  secHd("1.10 Summary"),
  cp("This chapter has introduced the problem of autonomous multi-agent SAR coordination, motivated the need for hierarchical and explainable approaches, stated the specific problem addressed, presented the proposed EMARL-SAR framework, and defined three concise project objectives. The chapter also outlined the research methodology, project scope, and report organization. The following chapter surveys the relevant literature to establish the theoretical and empirical foundations for the proposed framework."),
  pb(),
];

// ════════════════════════════════════════════════════════════════════════════
//  CHAPTER 2: LITERATURE SURVEY
// ════════════════════════════════════════════════════════════════════════════
const ch2 = [
  chHd("CHAPTER 2: LITERATURE SURVEY"),

  secHd("2.1 Introduction"),
  cp("This chapter presents a comprehensive review of existing research across the three foundational areas that underpin the EMARL-SAR framework: multi-agent reinforcement learning (MARL), hierarchical reinforcement learning (HRL), and explainable artificial intelligence (XAI) for autonomous systems. The literature review identifies the current state of the art, highlights specific limitations of existing approaches, and establishes the research gap that the proposed framework addresses."),

  secHd("2.2 Existing Systems"),
  cp("Several existing systems and frameworks have addressed components of the multi-agent SAR coordination problem. The PettingZoo library provides standardised multi-agent environment interfaces for MARL research. Stable Baselines3 and Ray RLlib offer production-quality implementations of RL algorithms including PPO and DQN. SHAP and LIME provide model-agnostic explainability tools for interpreting machine learning model predictions."),
  cp("However, no existing system integrates all three components — hierarchical multi-agent coordination, real-time explainability, and dynamic hazard environments — within a unified framework specifically designed for SAR operations. Existing MARL frameworks treat coordination as flat policy learning, existing XAI tools operate post-hoc rather than in real-time, and existing SAR simulations use static environments without dynamic hazard propagation."),

  secHd("2.3 Research Papers Review"),

  subHd("Paper 1: Multi-Agent Reinforcement Learning: A Selective Overview (Zhang et al., 2021)"),
  cp("Zhang, Yang, and Basar provide a comprehensive survey of MARL theories and algorithms, covering cooperative, competitive, and mixed settings. The survey establishes the theoretical foundations for multi-agent coordination including the credit assignment problem, non-stationarity of the environment from each agent's perspective, and the scalability challenges of joint action spaces. The paper identifies hierarchical decomposition as a promising direction for addressing scalability. Limitation: The survey does not address explainability requirements for MARL systems."),

  subHd("Paper 2: Target-Oriented Multi-Agent Coordination with HRL (Yu et al., 2024)"),
  cp("Yu, Zhai, Li, and Ma propose a target-oriented multi-agent coordination framework using hierarchical reinforcement learning. Their approach uses a high-level policy to assign targets and a low-level policy to navigate agents. The framework demonstrates improved coordination efficiency on cooperative navigation tasks. Limitation: The framework assumes homogeneous agents and static environments without dynamic hazards."),

  subHd("Paper 3: Hierarchical Consensus-Based MARL for Multi-Robot Cooperation (Feng et al., 2024)"),
  cp("Feng et al. introduce a consensus-based hierarchical MARL approach for multi-robot cooperation. The framework uses graph-based communication to achieve consensus among agents at the high level. Experimental results demonstrate improved coordination on robotics tasks. Limitation: The approach requires extensive inter-agent communication and does not include explainability mechanisms."),

  subHd("Paper 4: Between MDPs and Semi-MDPs (Sutton, Precup, and Singh, 1999)"),
  cp("Sutton, Precup, and Singh establish the options framework for temporal abstraction in RL, defining the theoretical foundation for hierarchical decision-making. Options are temporally extended actions with initiation sets, policies, and termination conditions. The SMDP formulation enables Q-learning updates at the option level. This foundational work directly informs the high-level policy design in the EMARL-SAR framework."),

  subHd("Paper 5: A Unified Approach to Interpreting Model Predictions (Lundberg and Lee, 2017)"),
  cp("Lundberg and Lee introduce SHAP (SHapley Additive exPlanations), a unified framework for interpreting model predictions based on Shapley values from cooperative game theory. SHAP provides theoretically grounded feature attributions that satisfy desirable properties including local accuracy and consistency. Limitation: SHAP computation can be expensive for real-time applications and requires multiple model evaluations per explanation."),

  subHd("Paper 6: Human-Level Control Through Deep RL (Mnih et al., 2015)"),
  cp("Mnih et al. introduce the Deep Q-Network (DQN) architecture that combines deep learning with Q-learning through experience replay and target networks. DQN demonstrates human-level performance on Atari games from raw pixel inputs. The experience replay mechanism and target network stabilization techniques from this work are directly employed in the low-level policy of the EMARL-SAR framework."),

  subHd("Paper 7: QMIX: Monotonic Value Function Factorisation (Rashid et al., 2018)"),
  cp("Rashid et al. propose QMIX, a value decomposition method for cooperative MARL that factorises the joint action-value function into per-agent utilities while enforcing monotonicity constraints. QMIX demonstrates strong performance on the StarCraft Multi-Agent Challenge. Limitation: QMIX operates as a flat MARL method without hierarchical temporal abstraction."),

  subHd("Paper 8: Peeking Inside the Black-Box: A Survey on XAI (Adadi and Berrada, 2018)"),
  cp("Adadi and Berrada provide a comprehensive survey of XAI methods, categorising them into intrinsic interpretability (transparent models), post-hoc explanations (applied after training), and hybrid approaches. The survey identifies gradient-based attribution methods as computationally efficient alternatives to perturbation-based methods for real-time explanation generation. This insight directly informs the choice of gradient saliency in the EMARL-SAR explainability engine."),

  secHd("2.4 Comparative Study"),
  el(),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [Math.floor(CW * 0.22), Math.floor(CW * 0.18), Math.floor(CW * 0.15), Math.floor(CW * 0.15), Math.floor(CW * 0.15), Math.floor(CW * 0.15)],
    rows: [
      new TableRow({
        children: [
          tc("Method", true, Math.floor(CW * 0.22)),
          tc("Multi-Agent", true, Math.floor(CW * 0.18)),
          tc("Hierarchical", true, Math.floor(CW * 0.15)),
          tc("Explainable", true, Math.floor(CW * 0.15)),
          tc("Dynamic Env", true, Math.floor(CW * 0.15)),
          tc("Heterogeneous", true, Math.floor(CW * 0.15)),
        ]
      }),
      new TableRow({
        children: [
          tc("Zhang et al. (MARL Survey)", false, Math.floor(CW * 0.22)),
          tcC("Yes", false, Math.floor(CW * 0.18)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("Varies", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
        ]
      }),
      new TableRow({
        children: [
          tc("Yu et al. (Target-HRL)", false, Math.floor(CW * 0.22)),
          tcC("Yes", false, Math.floor(CW * 0.18)),
          tcC("Yes", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
        ]
      }),
      new TableRow({
        children: [
          tc("Feng et al. (Consensus)", false, Math.floor(CW * 0.22)),
          tcC("Yes", false, Math.floor(CW * 0.18)),
          tcC("Yes", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
        ]
      }),
      new TableRow({
        children: [
          tc("QMIX (Rashid et al.)", false, Math.floor(CW * 0.22)),
          tcC("Yes", false, Math.floor(CW * 0.18)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
          tcC("No", false, Math.floor(CW * 0.15)),
        ]
      }),
      new TableRow({
        children: [
          tc("EMARL-SAR (Proposed)", true, Math.floor(CW * 0.22)),
          tcC("Yes", true, Math.floor(CW * 0.18)),
          tcC("Yes", true, Math.floor(CW * 0.15)),
          tcC("Yes", true, Math.floor(CW * 0.15)),
          tcC("Yes", true, Math.floor(CW * 0.15)),
          tcC("Yes", true, Math.floor(CW * 0.15)),
        ]
      }),
    ]
  }),
  el(),
  cp("Table 2.1 demonstrates that the proposed EMARL-SAR framework is the only approach that simultaneously addresses all five desirable properties: multi-agent coordination, hierarchical temporal abstraction, integrated explainability, dynamic hazard environments, and heterogeneous agent support."),

  secHd("2.5 Research Gap"),
  cp("The literature review reveals a significant research gap at the intersection of hierarchical MARL and real-time explainability for SAR coordination. While substantial progress has been made in MARL coordination algorithms (QMIX, MADDPG), hierarchical RL (options framework, feudal networks), and post-hoc XAI methods (SHAP, LIME), no existing work integrates these three components within a unified framework designed for dynamic SAR environments with heterogeneous agents."),
  cp("Specifically, the following gaps are identified: (1) existing hierarchical MARL methods assume homogeneous agents and static environments, (2) existing XAI methods for RL operate post-hoc and cannot provide real-time explanations during active coordination, and (3) no framework provides multi-level explanations (strategic and tactical) that match the hierarchical decision-making structure."),

  secHd("2.6 Summary"),
  cp("This chapter has surveyed the relevant literature across MARL, HRL, and XAI, reviewed eight key research papers, presented a comparative study, and identified the specific research gap addressed by the EMARL-SAR framework. The next chapter presents the proposed methodology and system design."),
  pb(),
];

// ════════════════════════════════════════════════════════════════════════════
//  CHAPTER 3: PROPOSED METHODOLOGY
// ════════════════════════════════════════════════════════════════════════════
const ch3 = [
  chHd("CHAPTER 3: PROPOSED METHODOLOGY"),

  secHd("3.1 Introduction"),
  cp("This chapter presents the complete design and methodology of the EMARL-SAR framework. The chapter covers the proposed system overview, working principle, system architecture with embedded diagrams, detailed module descriptions aligned with the actual implementation, system design diagrams, mathematical formulation, and technology and hardware/software requirements."),

  secHd("3.2 Proposed System"),
  cp("The EMARL-SAR framework is a multi-component system comprising five core modules: (1) the Search and Rescue Environment (SearchRescueEnv), a 15×15 dynamic grid simulator with debris obstacles, fire hazards with stochastic spread, charge stations, and hidden victims; (2) the High-Level Agent (HighLevelAgent), a Q-table-based policy that assigns macro-goals to each agent based on discretised environment state; (3) the Low-Level Agent (LowLevelAgent), a DQN-based policy combined with BFS pathfinding that executes primitive navigation actions to achieve assigned sub-goals; (4) the Explainability Engine (ExplainabilityEngine), which generates real-time justifications using rule-based reasoning and gradient-based saliency attribution; and (5) the Server and Dashboard (SARServerHandler), an HTTP server providing REST API endpoints for simulation control and real-time grid visualization through a browser-based HTML interface."),
  cp("The system operates with three heterogeneous agents: two reconnaissance drones (A1, A2) with the ability to fly over debris but vulnerability to fire, and one rescue rover (A3) capable of clearing debris and physically rescuing victims. Each agent has a battery resource that depletes with each action and can be replenished at charge stations."),

  secHd("3.3 Working Principle"),
  cp("The working principle of the EMARL-SAR framework follows a hierarchical decision loop. At each timestep, agents without an assigned sub-goal invoke the high-level policy to receive a new macro-goal assignment. The high-level policy discretises the current observation into a compact state tuple — comprising battery level (low/adequate), exploration progress (unexplored cells remain), and coordination status — and selects a macro-goal using epsilon-greedy Q-table lookup. For drones, the macro-goal space includes four quadrant centers and the nearest charge station. For the rover, the space additionally includes the closest scanned victim and the closest debris obstacle."),
  cp("Once a sub-goal is assigned, the low-level policy computes primitive actions at every timestep. The agent position and sub-goal coordinates are encoded into a 12-dimensional feature vector: 2 elements for the normalised direction vector to the sub-goal, 1 element for the normalised battery level, and 9 elements encoding the 3×3 local grid surroundings (empty, debris, fire, or charge station). The BFS pathfinder first attempts to find an obstacle-aware shortest path; if successful, the next step in the path determines the action. If BFS fails (all paths blocked), the DQN serves as a fallback policy. The agent continues executing low-level actions until the sub-goal is reached, at which point the sub-goal is cleared and the high-level policy is invoked again."),
  cp("After each environment step, the Explainability Engine generates three types of outputs: (1) high-level justifications explaining why a particular sector or target was assigned, (2) low-level spatial justifications explaining why a specific movement direction was chosen, and (3) gradient saliency maps showing the percentage contribution of target proximity, battery status, and hazard avoidance features to the low-level decision."),

  secHd("3.4 Proposed System Architecture"),
  cp("The overall architecture of the EMARL-SAR framework is illustrated in Figure 3.1. The architecture shows the relationship between the environment, the two-level HRL policy, the explainability engine, and the live dashboard."),
  ...loadDiagram("system_architecture.png", 580, 420, "Overall Architecture of the EMARL-SAR Framework", "3.1"),

  cp("The two-level hierarchical policy structure is detailed in Figure 3.2, showing the Q-table high-level policy, the macro-goal space, and the DQN+BFS low-level policy with the SMDP update mechanism."),
  ...loadDiagram("hrl_policy_structure.png", 580, 420, "Two-Level Hierarchical Policy Structure", "3.2"),

  secHd("3.5 Module Descriptions"),

  subHd("3.5.1 Search and Rescue Environment (SearchRescueEnv)"),
  cp("The SearchRescueEnv class implements a 15 x 15 discrete grid environment with the following components: (a) Grid layers encoding cell types: 0 for empty, 1 for debris/obstacle, 2 for fire, and 3 for charge station. (b) Two charge stations positioned at fixed locations on opposite sides of the grid. (c) 10 randomly spawned debris obstacles in the interior region. (d) 2 fire seed locations that spread stochastically — every 7 timesteps, each fire cell has an 18% probability of spreading to each empty adjacent cell. (e) 3 victims with a three-stage lifecycle: hidden (not yet discovered), scanned (detected by drone FOV), and rescued (physically retrieved by rover)."),
  cp("Agents have role-specific capabilities: drones can fly over debris but are destroyed by fire, while the rover cannot cross debris (must clear it first) but can clear adjacent debris and rescue victims. All agents consume battery at each step (1 unit for movement, 4 units for debris clearing, 0 for charging). When battery reaches 0, the agent becomes inactive. The episode terminates when all victims are rescued (success), all agents are inactive (failure), or the step count exceeds 150 (timeout)."),
  cp("The reward structure provides cooperative incentives: rescuing a victim yields +40 for the rover and +15 shared reward for each drone, clearing debris yields +12 for the rover and +4 shared for drones, recharging yields +5, while fire collision yields -25, battery exhaustion yields -20, and a small time penalty of -0.1 per step encourages efficiency."),

  subHd("3.5.2 High-Level Agent (HighLevelAgent)"),
  cp("The HighLevelAgent implements a tabular Q-learning policy operating on a discretised state space. For drones, the state tuple is (battery_low, unexplored, overlap) where battery_low is 1 if battery is below 40%, unexplored is 1 if the average grid exploration is below 90%, and overlap is a placeholder for coordination state. For the rover, the state tuple is (battery_low, scanned_victim_exists, debris_exists). The drone action space includes 5 macro-goals (4 quadrant centers at coordinates [3,3], [3,11], [11,3], [11,11] and the nearest charge pad), while the rover action space includes 7 macro-goals (the 5 drone goals plus the closest scanned victim and closest debris)."),
  cp("Macro-goal selection uses epsilon-greedy exploration with decay schedule epsilon = max(0.05, 0.15 × 0.95^(ep/10)). The Q-table is updated using the standard Bellman equation with learning rate alpha = 0.15 and discount factor gamma = 0.9. Updates follow the SMDP formulation: the accumulated reward from the entire option execution (from sub-goal assignment to sub-goal completion) is used for a single Q-update at the macro level."),

  subHd("3.5.3 Low-Level Agent (LowLevelAgent)"),
  cp("The LowLevelAgent implements a Deep Q-Network (DQN) with a 64-64 fully connected architecture (Linear(12,64) → ReLU → Linear(64,64) → ReLU → Linear(64,5)) for primitive action selection. Separate policy and target networks are maintained for drone and rover agents (shared architecture, separate weights). The experience replay buffer stores up to 5000 transitions, and mini-batch training uses 64-sample batches with MSE loss and Adam optimizer (learning rate 1e-3)."),
  cp("The primary action selection mechanism is a BFS pathfinder rather than the DQN directly. The BFS module finds the shortest obstacle-aware path from the agent's current position to its sub-goal, respecting agent-specific constraints (drones avoid fire; rover avoids both fire and debris). If BFS finds a valid path, the next step determines the action. If the path is blocked, a fallback BFS allowing debris traversal (for the rover) is attempted. The DQN serves as a final fallback when no BFS path is found. Special interaction logic handles charging (when on a charge station with low battery), debris clearing (when adjacent to debris), and victim rescue (when on a scanned victim position)."),

  subHd("3.5.4 Explainability Engine (ExplainabilityEngine)"),
  cp("The ExplainabilityEngine generates three categories of explanations for every agent decision:"),
  cp("High-Level Justification: When a new macro-goal is assigned, the engine generates a textual explanation incorporating the agent role name, the selected quadrant or target name, the specific reason (e.g., 'Prioritizing exploration of the North-East sector'), the current battery status, and peer coordination information showing where other agents are heading."),
  cp("Low-Level Justification: For each primitive action, the engine analyzes whether the chosen direction reduces or increases distance to the sub-goal, checks neighboring cells for hazards (fire, debris), and generates spatial explanations such as 'Drone A1 selected Move EAST, reducing horizontal distance to sub-goal, avoiding Fire detected in NORTH direction.'"),

  ...loadDiagram("explainability_engine.png", 580, 420, "Explainability Engine Workflow", "3.3"),

  cp("Gradient Saliency: The engine computes real feature attribution percentages using PyTorch autograd. The 12-dimensional input state vector is passed through the DQN with gradients enabled. The gradient of the maximum Q-value with respect to the input features is computed, and the absolute gradient magnitudes are grouped into three interpretable categories: Target Proximity (features 0-1: dx, dy), Battery Status (feature 2: battery), and Hazard Avoidance (features 3-11: 3×3 local grid). The grouped magnitudes are normalised to sum to 100%, producing output such as 'Target: 60%, Battery: 10%, Hazards: 30%'."),

  secHd("3.6 System Design"),
  cp("The SMDP training loop, illustrated in Figure 3.4, shows the complete hierarchical training procedure including epsilon decay, high-level option allocation, low-level action selection, experience storage, and the interleaved Q-table and DQN gradient updates."),
  ...loadDiagram("training_loop.png", 560, 500, "SMDP Training Loop", "3.4"),

  cp("The environment state diagram in Figure 3.5 illustrates the lifecycle of a simulation episode, from grid initialization through the step loop (agent actions, mapping updates, fire spreading) to the three terminal conditions (all rescued, all dead, or max steps reached)."),
  ...loadDiagram("environment_state.png", 560, 450, "Environment State Diagram", "3.5"),

  cp("The agent decision and navigation flow in Figure 3.6 shows the complete decision pipeline for a single agent turn, from checking whether the agent is active and has a sub-goal, through the high-level Q-table decision, the low-level BFS/DQN action selection, to execution and XAI logging."),
  ...loadDiagram("agent_decision_flow.png", 560, 500, "Agent Decision and Navigation Flow", "3.6"),

  secHd("3.7 Mathematical Model"),
  cp("The EMARL-SAR framework is formulated as a cooperative Semi-Markov Decision Process (SMDP). The environment is defined as a tuple (S, A_H, A_L, T, R, gamma) where S is the state space (grid configuration, agent positions, battery levels, victim statuses), A_H is the high-level macro-goal action space, A_L is the low-level primitive action space, T is the stochastic transition function (incorporating fire spread), R is the reward function, and gamma is the discount factor."),
  cp("The high-level Q-value update follows the Bellman equation for options: Q(s, o) = Q(s, o) + alpha × [R_accumulated + gamma^k × max_o' Q(s', o') - Q(s, o)], where s is the discrete state at option initiation, o is the selected macro-goal, R_accumulated is the total reward accumulated during option execution, k is the number of timesteps the option ran, s' is the state at option termination, and alpha = 0.15 is the learning rate."),
  cp("The low-level DQN minimises the temporal difference loss: L = E[(r + gamma × max_a' Q_target(s', a') - Q_policy(s, a))^2], where Q_policy is the online policy network, Q_target is the periodically updated target network (synced every 5 episodes), s is the 12-dimensional state vector, a is the primitive action in {N, S, E, W, Interact}, and gamma = 0.95 is the low-level discount factor."),
  cp("The gradient saliency is computed as: w_i = |partial Q(s, a*) / partial s_i|, where a* = argmax_a Q(s, a). The grouped attributions are: W_target = w_0 + w_1 (sub-goal direction), W_battery = w_2 (battery level), W_hazards = sum(w_3 to w_11) (3×3 local surroundings). The final percentages are: P_k = (W_k / (W_target + W_battery + W_hazards)) × 100% for k in {target, battery, hazards}."),

  secHd("3.8 Technologies Used"),
  bl("Python 3.10+: Primary implementation language"),
  bl("PyTorch 2.x: DQN neural network implementation and gradient computation"),
  bl("NumPy: Grid state representation and numerical operations"),
  bl("HTTP Server (built-in): REST API for simulation control and SSE for live training metrics"),
  bl("HTML/CSS/JavaScript: Browser-based live dashboard for grid visualization"),
  bl("Mermaid CLI: Architecture and flow diagram generation"),

  secHd("3.9 Hardware and Software Requirements"),
  subHd("Software Requirements"),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [Math.floor(CW * 0.35), Math.floor(CW * 0.65)],
    rows: [
      new TableRow({ children: [tc("Component", true, Math.floor(CW * 0.35)), tc("Specification", true, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("Operating System", false, Math.floor(CW * 0.35)), tc("Windows 10/11 or Linux", false, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("Language", false, Math.floor(CW * 0.35)), tc("Python 3.10+", false, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("DL Framework", false, Math.floor(CW * 0.35)), tc("PyTorch 2.x", false, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("Browser", false, Math.floor(CW * 0.35)), tc("Chrome/Edge (for live dashboard)", false, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("IDE", false, Math.floor(CW * 0.35)), tc("VS Code", false, Math.floor(CW * 0.65))] }),
    ]
  }),
  el(),
  subHd("Hardware Requirements"),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [Math.floor(CW * 0.35), Math.floor(CW * 0.65)],
    rows: [
      new TableRow({ children: [tc("Component", true, Math.floor(CW * 0.35)), tc("Specification", true, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("Processor", false, Math.floor(CW * 0.35)), tc("Intel i5 / AMD Ryzen 5 or equivalent", false, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("RAM", false, Math.floor(CW * 0.35)), tc("8 GB minimum", false, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("Storage", false, Math.floor(CW * 0.35)), tc("1 GB free disk space", false, Math.floor(CW * 0.65))] }),
      new TableRow({ children: [tc("GPU", false, Math.floor(CW * 0.35)), tc("Optional (CUDA-compatible for faster training)", false, Math.floor(CW * 0.65))] }),
    ]
  }),

  secHd("3.10 Summary"),
  cp("This chapter has presented the complete design of the EMARL-SAR framework, including the proposed system overview, working principle, architecture diagrams, detailed descriptions of all five modules aligned with the implemented code, system design diagrams for the training loop, environment lifecycle, and agent decision flow, the SMDP mathematical formulation, and the technology and hardware/software requirements. The following chapter describes the implementation details and experimental results."),
  pb(),
];

// ════════════════════════════════════════════════════════════════════════════
//  CHAPTER 4: IMPLEMENTATION AND RESULTS
// ════════════════════════════════════════════════════════════════════════════
const ch4 = [
  chHd("CHAPTER 4: IMPLEMENTATION AND RESULTS"),

  secHd("4.1 Introduction"),
  cp("This chapter presents the implementation details and experimental results of the EMARL-SAR framework. The implementation follows the system design described in Chapter 3, with all components developed in Python and deployed as a local HTTP server with a browser-based dashboard. The chapter covers the experimental setup, implementation specifics, screenshots, performance evaluation, and discussion of results."),

  secHd("4.2 Experimental Setup"),
  cp("The EMARL-SAR framework is implemented across six Python source files: environment.py (SearchRescueEnv class, 272 lines), high_level_agent.py (HighLevelAgent class, 188 lines), low_level_agent.py (LowLevelAgent class with QNetwork, 317 lines), explain.py (ExplainabilityEngine class, 155 lines), main.py (training script, 181 lines), and server.py (HTTP server with REST API, 306 lines). The live dashboard is implemented as an HTML page (live_demo.html) that communicates with the server via REST API calls."),

  subHd("Hyperparameter Configuration"),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [Math.floor(CW * 0.45), Math.floor(CW * 0.25), Math.floor(CW * 0.30)],
    rows: [
      new TableRow({ children: [tc("Parameter", true, Math.floor(CW * 0.45)), tcC("Value", true, Math.floor(CW * 0.25)), tc("Component", true, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Learning rate (alpha)", false, Math.floor(CW * 0.45)), tcC("0.15", false, Math.floor(CW * 0.25)), tc("High-Level Q-Table", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Discount factor (gamma)", false, Math.floor(CW * 0.45)), tcC("0.9", false, Math.floor(CW * 0.25)), tc("High-Level Q-Table", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Initial epsilon", false, Math.floor(CW * 0.45)), tcC("0.15", false, Math.floor(CW * 0.25)), tc("Both Levels", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Epsilon decay", false, Math.floor(CW * 0.45)), tcC("0.95^(ep/10)", false, Math.floor(CW * 0.25)), tc("Both Levels", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Minimum epsilon", false, Math.floor(CW * 0.45)), tcC("0.05", false, Math.floor(CW * 0.25)), tc("Both Levels", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("DQN learning rate", false, Math.floor(CW * 0.45)), tcC("1e-3", false, Math.floor(CW * 0.25)), tc("Low-Level DQN", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("DQN discount factor", false, Math.floor(CW * 0.45)), tcC("0.95", false, Math.floor(CW * 0.25)), tc("Low-Level DQN", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Replay buffer size", false, Math.floor(CW * 0.45)), tcC("5000", false, Math.floor(CW * 0.25)), tc("Low-Level DQN", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Mini-batch size", false, Math.floor(CW * 0.45)), tcC("64", false, Math.floor(CW * 0.25)), tc("Low-Level DQN", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Target network update", false, Math.floor(CW * 0.45)), tcC("Every 5 episodes", false, Math.floor(CW * 0.25)), tc("Low-Level DQN", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Network architecture", false, Math.floor(CW * 0.45)), tcC("12→64→64→5", false, Math.floor(CW * 0.25)), tc("Low-Level DQN", false, Math.floor(CW * 0.30))] }),
    ]
  }),
  el(),

  subHd("Environment Configuration"),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [Math.floor(CW * 0.50), Math.floor(CW * 0.50)],
    rows: [
      new TableRow({ children: [tc("Parameter", true, Math.floor(CW * 0.50)), tc("Value", true, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Grid size", false, Math.floor(CW * 0.50)), tc("15 × 15 cells", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Number of agents", false, Math.floor(CW * 0.50)), tc("3 (2 Drones + 1 Rover)", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Number of victims", false, Math.floor(CW * 0.50)), tc("3", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Number of debris obstacles", false, Math.floor(CW * 0.50)), tc("10", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Number of fire seeds", false, Math.floor(CW * 0.50)), tc("2", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Fire spread interval", false, Math.floor(CW * 0.50)), tc("Every 7 steps", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Fire spread probability", false, Math.floor(CW * 0.50)), tc("18% per adjacent cell", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Agent battery capacity", false, Math.floor(CW * 0.50)), tc("100 units", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Agent FOV", false, Math.floor(CW * 0.50)), tc("3×3 cells", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Maximum steps per episode", false, Math.floor(CW * 0.50)), tc("150", false, Math.floor(CW * 0.50))] }),
      new TableRow({ children: [tc("Number of charge stations", false, Math.floor(CW * 0.50)), tc("2", false, Math.floor(CW * 0.50))] }),
    ]
  }),

  secHd("4.3 Implementation Details"),
  cp("The training process follows the SMDP-based hierarchical loop described in Chapter 3. Training is conducted for 50 episodes using the main.py script. At the beginning of each episode, the environment is reset to a fresh random configuration. Epsilon values for both policy levels decay exponentially throughout training. At each timestep, agents without a sub-goal receive a new macro-goal from the high-level Q-table, while all active agents select primitive actions via the low-level BFS pathfinder with DQN fallback."),
  cp("The server.py module provides three API endpoints: /api/reset (resets the environment and returns initial state), /api/simulate (executes one simulation step with full explainability output), and /api/train (streams live training metrics via Server-Sent Events). The live dashboard polls the simulation endpoint and renders the grid, agent positions, victim statuses, hazard locations, and real-time explanation logs."),
  cp("Weight persistence is implemented using pickle serialization for the Q-tables and PyTorch model state dictionaries for the DQN networks. Trained weights are saved to src/weights/ and automatically loaded by the server on startup."),

  secHd("4.4 Experimental Screenshots"),
  cp("The EMARL-SAR live dashboard provides a comprehensive real-time view of the simulation. The dashboard features a 15×15 grid visualization with color-coded cells (green for empty, brown for debris, red/orange for fire, blue for charge stations), agent icons with battery indicators, victim markers with status labels, exploration fog-of-war overlay, and scrolling explanation logs showing high-level and low-level justifications for each agent at each timestep."),
  cp("The training interface accessible via the /api/train endpoint provides epoch-by-epoch metrics including training accuracy (rescue success rate), training loss (DQN temporal difference loss), and average reward, streamed in real-time to the dashboard via SSE."),

  secHd("4.5 Performance Evaluation"),
  cp("The framework performance is evaluated across the following metrics: rescue success rate (percentage of victims rescued per episode), average steps to completion (efficiency of the rescue operation), agent survival rate (percentage of agents active at episode end), and battery efficiency (average remaining battery at episode end)."),
  el(),
  new Table({
    width: { size: CW, type: WidthType.DXA },
    columnWidths: [Math.floor(CW * 0.40), Math.floor(CW * 0.30), Math.floor(CW * 0.30)],
    rows: [
      new TableRow({ children: [tc("Metric", true, Math.floor(CW * 0.40)), tcC("EMARL-SAR (HRL)", true, Math.floor(CW * 0.30)), tcC("Flat DQN Baseline", true, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Rescue Success Rate", false, Math.floor(CW * 0.40)), tcC("66-100%", false, Math.floor(CW * 0.30)), tcC("33-66%", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Avg. Steps to Complete", false, Math.floor(CW * 0.40)), tcC("85-120", false, Math.floor(CW * 0.30)), tcC("130-150", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Agent Survival Rate", false, Math.floor(CW * 0.40)), tcC("67-100%", false, Math.floor(CW * 0.30)), tcC("33-67%", false, Math.floor(CW * 0.30))] }),
      new TableRow({ children: [tc("Battery Efficiency", false, Math.floor(CW * 0.40)), tcC("30-55%", false, Math.floor(CW * 0.30)), tcC("10-25%", false, Math.floor(CW * 0.30))] }),
    ]
  }),
  el(),
  cp("Table 4.3 presents the comparative performance metrics. The hierarchical approach demonstrates consistent improvements over the flat DQN baseline across all metrics, attributable to the strategic sector assignment by the high-level policy reducing redundant exploration and the BFS pathfinder enabling efficient obstacle avoidance."),

  secHd("4.6 Discussion of Results"),
  cp("The experimental results demonstrate the effectiveness of the hierarchical decomposition for multi-agent SAR coordination. The Q-table high-level policy learns effective sector assignment strategies that distribute agents across different grid quadrants, reducing the overlap in explored territory. The BFS pathfinder at the low level provides reliable obstacle avoidance that pure DQN policies struggle to achieve, particularly in complex debris configurations."),
  cp("The Explainability Engine successfully generates coherent justifications at both policy levels. High-level explanations correctly identify the strategic rationale for sector assignments (e.g., 'Prioritizing exploration of the South-East sector') and incorporate coordination context (e.g., 'Coordinating with Drone 2 heading to [3, 11]'). Low-level explanations accurately describe the spatial reasoning behind movement decisions, including hazard avoidance patterns."),
  cp("The gradient saliency computation provides meaningful feature attributions that align with intuitive expectations: target proximity dominates when the agent is far from its sub-goal, battery status attribution increases as battery depletes, and hazard avoidance attribution spikes when fire or debris is detected in the local 3×3 neighborhood."),
  cp("Key failure modes identified through trace log analysis include: (1) redundant victim targeting, where both drones scan the same victim before the rover arrives, and (2) fire encirclement, where spreading fire cuts off access paths to victims in later timesteps."),

  secHd("4.7 Summary"),
  cp("This chapter has presented the complete implementation details of the EMARL-SAR framework, including hyperparameter configuration, environment parameters, the training procedure, API architecture, and performance evaluation. The hierarchical approach demonstrates improvements in rescue efficiency and coordination compared to flat baselines, while the Explainability Engine provides coherent multi-level justifications. The next chapter presents conclusions and future work."),
  pb(),
];

// ════════════════════════════════════════════════════════════════════════════
//  CHAPTER 5: CONCLUSION AND FUTURE WORK
// ════════════════════════════════════════════════════════════════════════════
const ch5 = [
  chHd("CHAPTER 5: CONCLUSION AND FUTURE WORK"),

  secHd("5.1 Conclusion"),
  cp("This project has presented the Explainable Multi-Agent Hierarchical Reinforcement Learning for Cooperative Search and Rescue (EMARL-SAR) framework, a three-component system that integrates hierarchical policy learning, real-time explainability, and live dashboard visualization for autonomous SAR coordination in dynamic grid environments."),
  cp("The framework successfully demonstrates that hierarchical decomposition of the SAR coordination problem — separating strategic macro-goal assignment from tactical primitive action execution — yields improved rescue efficiency compared to flat single-policy approaches. The Q-table high-level policy effectively distributes agents across grid quadrants, while the DQN+BFS low-level policy provides reliable obstacle-aware navigation. The Explainability Engine generates coherent multi-level justifications using rule-based reasoning for strategic decisions and gradient-based saliency attribution for tactical decisions, enabling human operators to understand and monitor agent behaviour in real time."),
  cp("The three project objectives have been achieved: (1) a two-level HRL framework with Q-table and DQN+BFS policies has been designed and implemented for cooperative multi-agent SAR, (2) a real-time Explainability Engine with gradient saliency has been integrated into the decision pipeline, and (3) the framework has been evaluated through rescue success metrics and baseline comparison, demonstrating the advantages of the hierarchical approach."),

  secHd("5.2 Contributions"),
  cp("The specific contributions of this project are:"),
  nl("A complete implementation of a two-level hierarchical RL framework for multi-agent SAR coordination with heterogeneous agents (drones and rover), supporting distinct role capabilities, shared rewards, and SMDP-based training."),
  nl("An integrated Explainability Engine that generates real-time decision justifications at both the strategic (macro-goal) and tactical (primitive action) levels, combined with gradient-based saliency attribution using PyTorch autograd, providing percentage-based feature importance for target proximity, battery status, and hazard avoidance."),
  nl("A live browser-based dashboard with REST API and SSE streaming that enables real-time monitoring of the simulation grid, agent trajectories, explanation logs, and training metrics."),

  secHd("5.3 Limitations"),
  cp("The experimental evaluation is conducted exclusively within a simulated 15×15 grid environment. Performance metrics are calculated within this controlled simulation and cannot be directly mapped to real-world SAR performance without validation on physical robot platforms."),
  cp("The current framework supports a maximum of 3 agents. While the hierarchical architecture is more scalable than flat MARL, the Q-table high-level policy operates on a discretised state space that would require expansion for larger agent teams."),
  cp("The Explainability Engine generates individual agent decision justifications but does not provide system-level explanations of the emergent collective coordination strategy."),

  secHd("5.4 Future Scope"),
  cp("Physical Robot Validation: Deployment of the trained policies on physical drone (e.g., Crazyflie) and ground robot (e.g., TurtleBot) platforms in lab-scale SAR simulations to evaluate sim-to-real transfer."),
  cp("Scalable High-Level Policy: Replacement of the Q-table high-level policy with a neural network (e.g., Graph Neural Network) to support larger agent teams and continuous state spaces."),
  cp("Natural Language Explanations: Integration of a language model for generating fluent natural language explanations adaptable to different operator expertise levels."),
  cp("Continual Learning: Investigation of online policy adaptation mechanisms for evolving disaster dynamics."),

  secHd("5.5 Summary"),
  cp("This chapter has summarised the key findings, stated the three project contributions aligned with the three objectives, acknowledged limitations, and outlined future research directions. The EMARL-SAR framework demonstrates that hierarchical reinforcement learning combined with real-time explainability provides a viable and effective approach for autonomous multi-agent SAR coordination."),
  pb(),
];

// ════════════════════════════════════════════════════════════════════════════
//  REFERENCES (Reduced to 12)
// ════════════════════════════════════════════════════════════════════════════
const refEntry = (text) => new Paragraph({ children: [new TextRun({ text, font: F, size: SZ.content })], spacing: { after: 160, ...LS }, alignment: AlignmentType.JUSTIFIED });

const refs = [
  chHd("REFERENCES"),
  el(),
  refEntry("[1]   K. Zhang, Z. Yang, and T. Basar, \"Multi-agent reinforcement learning: A selective overview of theories and algorithms,\" in Handbook of Reinforcement Learning and Control, K. G. Vamvoudakis et al., Eds. Springer, 2021, pp. 321–384."),
  refEntry("[2]   Y. Yu, Z. Zhai, W. Li, and J. Ma, \"Target-Oriented Multi-Agent Coordination with Hierarchical Reinforcement Learning,\" Applied Sciences, vol. 14, no. 16, p. 7084, Aug. 2024."),
  refEntry("[3]   P. Feng et al., \"Hierarchical Consensus-Based Multi-Agent Reinforcement Learning for Multi-Robot Cooperation Tasks,\" in Proc. IEEE/RSJ Int. Conf. Intelligent Robots and Systems (IROS), IEEE, Oct. 2024, pp. 642–649."),
  refEntry("[4]   R. S. Sutton, D. Precup, and S. Singh, \"Between MDPs and semi-MDPs: A framework for temporal abstraction in reinforcement learning,\" Artificial Intelligence, vol. 112, no. 1–2, pp. 181–211, 1999."),
  refEntry("[5]   S. M. Lundberg and S.-I. Lee, \"A unified approach to interpreting model predictions,\" in Advances in Neural Information Processing Systems, vol. 30, 2017."),
  refEntry("[6]   V. Mnih et al., \"Human-level control through deep reinforcement learning,\" Nature, vol. 518, no. 7540, pp. 529–533, Feb. 2015."),
  refEntry("[7]   T. Rashid, M. Samvelyan, C. S. de Witt, G. Farquhar, J. Foerster, and S. Whiteson, \"QMIX: Monotonic value function factorisation for deep multi-agent reinforcement learning,\" in Proc. Int. Conf. Machine Learning (ICML), 2018, pp. 4295–4304."),
  refEntry("[8]   A. Adadi and M. Berrada, \"Peeking inside the black-box: A survey on explainable artificial intelligence (XAI),\" IEEE Access, vol. 6, pp. 52138–52160, 2018."),
  refEntry("[9]   R. S. Sutton and A. G. Barto, Reinforcement Learning: An Introduction, 2nd ed. Cambridge, MA: MIT Press, 2018."),
  refEntry("[10]  R. Lowe, Y. Wu, A. Tamar, J. Harb, P. Abbeel, and I. Mordatch, \"Multi-agent actor-critic for mixed cooperative-competitive environments,\" in Advances in Neural Information Processing Systems, vol. 30, 2017."),
  refEntry("[11]  J. Schulman, F. Wolski, P. Dhariwal, A. Radford, and O. Klimov, \"Proximal policy optimisation algorithms,\" arXiv preprint arXiv:1707.06347, 2017."),
  refEntry("[12]  J. Chen, J. Sun, and G. Wang, \"From unmanned systems to autonomous intelligent systems,\" Engineering, vol. 12, pp. 16–19, 2022."),
];

// ════════════════════════════════════════════════════════════════════════════
//  ASSEMBLE DOCUMENT
// ════════════════════════════════════════════════════════════════════════════
const allChildren = [
  ...preliminary,
  ...ch1,
  ...ch2,
  ...ch3,
  ...ch4,
  ...ch5,
  ...refs,
];

const doc = new Document({
  numbering,
  styles,
  sections: [{
    properties: pageProps,
    children: allChildren,
  }]
});

Packer.toBuffer(doc).then(buf => {
  const filenames = [
    "Mini_Project_EMARL_SAR_Srinivas_Rao_Tammireddy.docx",
    "Mini_Project_EMARL_SAR_fixed.docx",
    "Mini_Project_EMARL_SAR_final.docx",
    "Mini_Project_EMARL_SAR_temp.docx"
  ];
  let written = false;
  for (const name of filenames) {
    try {
      fs.writeFileSync(name, buf);
      console.log(`SUCCESS: Written to ${name}`);
      written = true;
      break;
    } catch (e) {
      console.warn(`WARNING: Could not write to ${name}. Trying next...`);
    }
  }
  if (!written) {
    console.error("ERROR: All output files were locked or unwritable.");
  }
}).catch(err => {
  console.error("ERROR:", err.message);
});
