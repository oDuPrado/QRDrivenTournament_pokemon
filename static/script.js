// Constants and Global Variables
let totalTime = 1800; // 30 minute
let countdownInterval = null,
  playingInterval = null;
let lastData = null,
  roundStartTime = null;
let tournamentStarted = false,
  tournamentEnded = false;
let playingTables = {},
  playerStats = {},
  processedMatches = {};

// DOM Elements
const setupSection = document.getElementById("setup-section");
const tournamentSection = document.getElementById("tournament-section");
const scoreboardSection = document.getElementById("scoreboard-section");
const countdownTimer = document.getElementById("countdown-timer");
const tablesContainer = document.getElementById("tables-container");
const initialTablesContainer = document.getElementById(
  "initial-tables-container"
);
const roundInfoTitle = document.getElementById("round-info");
const playersCountInfo = document.getElementById("players-count");
const currentRoundSpan = document.getElementById("current-round");
const currentPlayersSpan = document.getElementById("current-players");
const scoreboardBody = document.querySelector("#scoreboard tbody");

// Buttons
document.getElementById("start-btn").addEventListener("click", startTournament);
document.getElementById("stats-btn").addEventListener("click", showStatistics);
document
  .getElementById("back-to-setup-btn")
  .addEventListener("click", backToSetup);
document.getElementById("next-round-btn").addEventListener("click", () => {
  window.open("report.html", "Relatorio", "width=600,height=400");
  resetTournament();
});

// WebSocket Setup
const socket = new WebSocket("ws://localhost:8765");
socket.onmessage = (event) => handleWebSocketMessage(event.data);

// Core Functions
function handleWebSocketMessage(dataStr) {
  try {
    const data = JSON.parse(dataStr);
    if (data.type === "update_results") updateResults(data.results);
    else if (!tournamentStarted) updateInitialView(data);
    else if (!tournamentEnded) updateTournamentView(data);
  } catch (e) {
    console.error("WebSocket Error:", e);
  }
}

function startTournament() {
  if (!lastData) return;
  tournamentStarted = true;
  switchView(tournamentSection);
  roundStartTime = Date.now();
  startCountdown();
  updateTournamentView(lastData);
}

function resetTournament() {
  Object.assign(this, { tournamentStarted: false, tournamentEnded: false });
  totalTime = 1800;
  playingTables = {};
  playerStats = {};
  processedMatches = {};
  clearIntervals();
  switchView(setupSection);
  if (lastData) updateInitialView(lastData);
}

function showStatistics() {
  switchView(scoreboardSection);
  renderScoreboard();
}

function backToSetup() {
  switchView(setupSection);
}

// View Updates
function updateInitialView(data) {
  const { tablesData, latestRound } = extractRoundData(data);
  renderInitialTables(tablesData);
  roundInfoTitle.textContent = `Rodada Atual: ${latestRound}`;
  playersCountInfo.textContent = `Número de Jogadores: ${
    Object.keys(data?.players || {}).length
  }`;
}

function updateTournamentView(data) {
  const { tablesData, latestRound } = extractRoundData(data);
  renderTables(tablesData);
  currentRoundSpan.textContent = `Rodada: ${latestRound}`;
  currentPlayersSpan.textContent = `Jogadores: ${
    Object.keys(data?.players || {}).length
  }`;
  processMatchData(data, tablesData);
}

// Table Rendering
function renderInitialTables(tablesData) {
  renderTables(tablesData, initialTablesContainer);
}

function renderTables(tablesData, container = tablesContainer) {
  container.innerHTML = "";
  Object.entries(tablesData).forEach(([tableId, tableInfo]) => {
    container.appendChild(createTableCard(tableId, tableInfo));
  });
}

function createTableCard(tableId, tableInfo) {
  const { player1, player2, outcome } = tableInfo;
  const card = createElement("div", { class: "table-card" });
  card.appendChild(createElement("h2", {}, `Mesa ${tableId}`));
  card.appendChild(
    createElement("p", { class: "players" }, `${player1} vs ${player2}`)
  );
  if (tournamentStarted)
    card.appendChild(
      createElement("p", { class: "status" }, `Status: ${outcome}`)
    );
  return card;
}

// Utilities
function switchView(target) {
  [setupSection, tournamentSection, scoreboardSection].forEach((section) =>
    section.classList.add("hidden")
  );
  target.classList.remove("hidden");
}

function clearIntervals() {
  [countdownInterval, playingInterval].forEach((interval) =>
    clearInterval(interval)
  );
  countdownInterval = playingInterval = null;
}

function extractRoundData(data) {
  const rounds = data.round || {};
  const latestRound = Math.max(...Object.keys(rounds).map(Number));
  const tablesData =
    rounds[latestRound]?.[Object.keys(rounds[latestRound])[0]]?.table || {};
  return { tablesData, latestRound };
}

function createElement(tag, attributes = {}, textContent = "") {
  const element = document.createElement(tag);
  Object.entries(attributes).forEach(([key, value]) =>
    element.setAttribute(key, value)
  );
  element.textContent = textContent;
  return element;
}
