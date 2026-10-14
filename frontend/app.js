"use strict";

const API_BASE = "/api";
const TITLE_MAX_LENGTH = 100;
const DESCRIPTION_MAX_LENGTH = 2000;
const SEARCH_DELAY_MS = 300;
const STATUSES = [
  { value: "TODO", label: "할 일" },
  { value: "DOING", label: "진행 중" },
  { value: "DONE", label: "완료" },
];
const PRIORITIES = [
  { value: "HIGH", label: "높음" },
  { value: "NORMAL", label: "보통" },
  { value: "LOW", label: "낮음" },
];
const DEFAULT_PRIORITY = "NORMAL";
const VISIBILITIES = [
  { value: "PRIVATE", label: "개인" },
  { value: "TEAM", label: "팀" },
];
const TEAM_NAME_MAX_LENGTH = 50;
const USERNAME_PATTERN = /^[a-z0-9_]{3,30}$/;
const PASSWORD_MIN_LENGTH = 8;
const PASSWORD_MAX_LENGTH = 128;
// 주소(#/...)별 화면. 로그인 여부에 따라 들어갈 수 있는 화면이 다르다.
const ROUTES = {
  "#/welcome": { view: "welcome", title: "시작", needsLogin: false },
  "#/login": { view: "login", title: "로그인", needsLogin: false },
  "#/signup": { view: "signup", title: "회원가입", needsLogin: false },
  "#/": { view: "tasks", title: "할 일", needsLogin: true },
  "#/teams": { view: "teams", title: "팀", needsLogin: true },
};
const DEFAULT_ROUTE = "#/";
const LOGIN_ROUTE = "#/login";
// 로그인하지 않은 사용자가 처음 보는 화면(로그인·회원가입 버튼).
const WELCOME_ROUTE = "#/welcome";

// 로그인한 사용자({id, username}). 로그인하지 않았으면 null.
let currentUser = null;
// 내가 속한 팀 목록(GET /api/teams). 할 일의 팀 선택과 범위 필터에 사용한다.
let myTeams = [];
// 팀 화면: 팀별 멤버 목록과 팀별 오류 문구.
let teamDetails = [];
const teamErrors = new Map();

// 마지막으로 API에서 받은 목록(검색·필터 적용 결과).
let tasks = [];
let loadFailed = false;
// 늦게 도착한 이전 목록 응답이 최신 결과를 덮어쓰지 않도록 요청 번호를 비교한다.
let listRequestId = 0;
let searchTimer = null;
// 수정 중인 항목의 id. 한 번에 하나만 수정한다.
let editingId = null;
let editError = "";
// 수정을 시작하거나 수정 오류가 났을 때만 수정 입력칸으로 포커스를 옮긴다.
let focusEditForm = false;
// 제목 검색, 상태, 우선순위 필터. 빈 값은 조건 없음이며 API에서 AND로 적용한다.
// scope: ""(전체), "mine", "team:<id>".
const filters = { query: "", status: "", priority: "", scope: "" };

const form = document.getElementById("task-form");
const titleInput = document.getElementById("task-title");
const descriptionInput = document.getElementById("task-description");
const priorityInput = document.getElementById("task-priority");
const dueInput = document.getElementById("task-due");
const submitButton = document.getElementById("submit-button");
const formError = document.getElementById("form-error");
const apiError = document.getElementById("api-error");
const searchInput = document.getElementById("search-input");
const statusFilter = document.getElementById("filter-status");
const priorityFilter = document.getElementById("filter-priority");
const taskList = document.getElementById("task-list");
const taskCount = document.getElementById("task-count");
const emptyMessage = document.getElementById("empty-message");
const visibilityInput = document.getElementById("task-visibility");
const teamField = document.getElementById("task-team-field");
const teamInput = document.getElementById("task-team");
const noTeamHelp = document.getElementById("no-team-help");
const scopeFilter = document.getElementById("filter-scope");
const navLinks = { tasks: document.getElementById("nav-tasks"), teams: document.getElementById("nav-teams") };
const teamForm = document.getElementById("team-form");
const teamNameInput = document.getElementById("team-name");
const teamButton = document.getElementById("team-button");
const teamError = document.getElementById("team-error");
const teamsEmpty = document.getElementById("teams-empty");
const teamList = document.getElementById("team-list");
const loadingMessage = document.getElementById("loading-message");
const userBar = document.getElementById("user-bar");
const guestBar = document.getElementById("guest-bar");
const guestLinks = { login: document.getElementById("guest-login"), signup: document.getElementById("guest-signup") };
const currentUsername = document.getElementById("current-username");
const logoutButton = document.getElementById("logout-button");
const views = {
  welcome: document.getElementById("welcome-view"),
  login: document.getElementById("login-view"),
  signup: document.getElementById("signup-view"),
  tasks: document.getElementById("tasks-view"),
  teams: document.getElementById("teams-view"),
};
const loginForm = document.getElementById("login-form");
const loginUsername = document.getElementById("login-username");
const loginPassword = document.getElementById("login-password");
const loginButton = document.getElementById("login-button");
const loginError = document.getElementById("login-error");
const loginNotice = document.getElementById("login-notice");
const signupForm = document.getElementById("signup-form");
const signupUsername = document.getElementById("signup-username");
const signupPassword = document.getElementById("signup-password");
const signupButton = document.getElementById("signup-button");
const signupError = document.getElementById("signup-error");

class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

// FastAPI 오류 응답({"detail": ...})을 화면에 보여 줄 문장으로 바꾼다.
function errorMessage(body, status) {
  if (body && Array.isArray(body.detail) && body.detail.length > 0) {
    return body.detail.map((item) => String(item.msg).replace(/^Value error, /, "")).join(" ");
  }
  if (body && typeof body.detail === "string") {
    return body.detail;
  }
  return `요청을 처리하지 못했습니다. (HTTP ${status})`;
}

async function request(method, path, body) {
  const options = { method };
  if (body !== undefined) {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(body);
  }

  let response;
  try {
    response = await window.fetch(`${API_BASE}${path}`, options);
  } catch (networkError) {
    throw new ApiError("API 서버에 연결할 수 없습니다. 서버가 실행 중인지 확인하세요.", 0);
  }

  if (response.status === 204) {
    return null;
  }
  let data = null;
  try {
    data = await response.json();
  } catch (parseError) {
    data = null;
  }
  if (!response.ok) {
    // 할 일 등 로그인이 필요한 요청에서 401이면 세션이 만료·로그아웃된 것이므로 로그인 화면으로 보낸다.
    if (response.status === 401 && !path.startsWith("/auth/")) {
      handleSessionExpired();
    }
    throw new ApiError(errorMessage(data, response.status), response.status);
  }
  return data;
}

function textLength(value) {
  return Array.from(value).length;
}

// 검증 실패 시 오류 메시지, 통과 시 null을 반환한다. 서버도 같은 규칙으로 다시 검증한다.
function validateTitle(title) {
  const length = textLength(title);
  if (length === 0) {
    return "제목을 입력하세요.";
  }
  if (length > TITLE_MAX_LENGTH) {
    return `제목은 ${TITLE_MAX_LENGTH}자 이하로 입력하세요. (현재 ${length}자)`;
  }
  return null;
}

function validateDescription(description) {
  const length = textLength(description);
  if (length > DESCRIPTION_MAX_LENGTH) {
    return `설명은 ${DESCRIPTION_MAX_LENGTH}자 이하로 입력하세요. (현재 ${length}자)`;
  }
  return null;
}

// YYYY-MM-DD 형식이면서 실제 존재하는 날짜인지 확인한다.
function isValidDate(value) {
  if (typeof value !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(value)) {
    return false;
  }
  const [year, month, day] = value.split("-").map(Number);
  const date = new Date(year, month - 1, day);
  return (
    date.getFullYear() === year &&
    date.getMonth() === month - 1 &&
    date.getDate() === day
  );
}

function validateTaskInput(input) {
  return (
    validateTitle(input.title) ||
    validateDescription(input.description) ||
    (isValidPriority(input.priority) ? null : "우선순위가 올바르지 않습니다.") ||
    (input.due_date !== null && !isValidDate(input.due_date)
      ? "마감일은 YYYY-MM-DD 형식의 올바른 날짜여야 합니다."
      : null) ||
    (input.visibility === "TEAM" && !input.team_id ? "팀을 선택하세요." : null)
  );
}

// 공개 범위 입력을 API 형식으로 바꾼다. PRIVATE이면 team_id는 null이다.
function readSharing(visibility, teamId) {
  return {
    visibility,
    team_id: visibility === "TEAM" && teamId !== "" ? Number(teamId) : null,
  };
}

function isOwner(task) {
  return currentUser !== null && task.owner.id === currentUser.id;
}

// 입력값을 API 요청 형식으로 정리한다. 빈 마감일은 null이다.
function readTaskInput(title, description, priority, dueDate) {
  return {
    title: title.trim(),
    description,
    priority,
    due_date: dueDate === "" ? null : dueDate,
  };
}

function isValidPriority(priority) {
  return PRIORITIES.some((item) => item.value === priority);
}

function labelOf(list, value) {
  const found = list.find((item) => item.value === value);
  return found ? found.label : value;
}

function findTask(id) {
  return tasks.find((task) => task.id === id);
}

function hasFilters() {
  return (
    filters.query.trim() !== "" || filters.status !== "" || filters.priority !== "" || filters.scope !== ""
  );
}

function listPath() {
  const params = new URLSearchParams();
  const query = filters.query.trim();
  if (query !== "") {
    params.set("q", query);
  }
  if (filters.status !== "") {
    params.set("status", filters.status);
  }
  if (filters.priority !== "") {
    params.set("priority", filters.priority);
  }
  if (filters.scope === "mine") {
    params.set("scope", "mine");
  } else if (filters.scope.startsWith("team:")) {
    params.set("scope", "team");
    params.set("team_id", filters.scope.slice("team:".length));
  }
  const queryString = params.toString();
  return queryString === "" ? "/tasks" : `/tasks?${queryString}`;
}

// API에서 현재 검색·필터 조건의 목록을 다시 받아 화면을 그린다.
async function loadTasks() {
  const requestId = ++listRequestId;
  try {
    const data = await request("GET", listPath());
    if (requestId !== listRequestId) {
      return;
    }
    tasks = data;
    loadFailed = false;
    apiError.textContent = "";
  } catch (error) {
    if (requestId !== listRequestId) {
      return;
    }
    if (error.status === 404 && filters.scope.startsWith("team:")) {
      // 그 사이 팀에서 빠졌으면 범위 필터를 전체로 되돌리고 팀 목록을 새로 받는다.
      filters.scope = "";
      await loadMyTeams();
      await loadTasks();
      return;
    }
    loadFailed = true;
    apiError.textContent = `목록을 불러오지 못했습니다. ${error.message}`;
  }
  render();
}

// 변경 요청을 보내고 결과와 관계없이 목록을 다시 받는다. 실패하면 오류를 표시한다.
async function runAction(action) {
  let message = "";
  try {
    await action();
  } catch (error) {
    message = error.message;
  }
  await loadTasks();
  if (message) {
    apiError.textContent = message;
  }
}

// 로컬 달력 기준 오늘 날짜(YYYY-MM-DD).
function todayString() {
  const now = new Date();
  const month = String(now.getMonth() + 1).padStart(2, "0");
  const day = String(now.getDate()).padStart(2, "0");
  return `${now.getFullYear()}-${month}-${day}`;
}

function isOverdue(task, today) {
  return task.due_date !== null && task.status !== "DONE" && task.due_date < today;
}

function changeStatus(id, status) {
  return runAction(() => request("PATCH", `/tasks/${id}`, { status }));
}

function startEdit(id) {
  editingId = id;
  editError = "";
  focusEditForm = true;
  render();
}

function cancelEdit() {
  editingId = null;
  editError = "";
  render();
}

function showEditError(message) {
  editError = message;
  focusEditForm = true;
  render();
}

async function saveEdit(id, input) {
  const error = validateTaskInput(input);
  if (error) {
    showEditError(error);
    return;
  }
  try {
    await request("PATCH", `/tasks/${id}`, input);
  } catch (requestError) {
    if (requestError.status === 404) {
      // 이미 삭제된 항목이면 수정 폼을 닫고 최신 목록을 보여 준다.
      editingId = null;
      editError = "";
      await loadTasks();
      apiError.textContent = requestError.message;
      return;
    }
    // 입력 오류나 연결 실패는 입력한 내용을 유지한 채 오류를 보여 준다.
    showEditError(requestError.message);
    return;
  }
  editingId = null;
  editError = "";
  await loadTasks();
}

function deleteTask(id) {
  const task = findTask(id);
  if (!task) {
    return Promise.resolve();
  }
  if (!window.confirm(`"${task.title}" 할 일을 삭제할까요?`)) {
    return Promise.resolve();
  }
  if (editingId === id) {
    editingId = null;
    editError = "";
  }
  return runAction(() => request("DELETE", `/tasks/${id}`));
}

function createButton(label, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.textContent = label;
  button.addEventListener("click", onClick);
  return button;
}

function createSelect(options, value, ariaLabel) {
  const select = document.createElement("select");
  select.setAttribute("aria-label", ariaLabel);
  for (const item of options) {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  }
  select.value = value;
  return select;
}

function createStatusSelect(task) {
  const select = createSelect(STATUSES, task.status, "상태");
  select.addEventListener("change", () => changeStatus(task.id, select.value));
  return select;
}

function createEditForm(task) {
  const container = document.createElement("div");
  container.className = "task-edit";

  const titleField = document.createElement("input");
  titleField.type = "text";
  titleField.value = task.title;
  titleField.setAttribute("aria-label", "제목 수정");

  const descriptionField = document.createElement("textarea");
  descriptionField.rows = 3;
  descriptionField.value = task.description;
  descriptionField.setAttribute("aria-label", "설명 수정");
  descriptionField.placeholder = "설명 (최대 2000자)";

  const priorityField = createSelect(PRIORITIES, task.priority, "우선순위 수정");

  const dueField = document.createElement("input");
  dueField.type = "date";
  dueField.value = task.due_date === null ? "" : task.due_date;
  dueField.setAttribute("aria-label", "마감일 수정");

  // 공개 범위와 팀은 작성자만 바꿀 수 있다.
  const owner = isOwner(task);
  let visibilityField = null;
  let teamSelect = null;
  if (owner) {
    visibilityField = createSelect(VISIBILITIES, task.visibility, "공개 범위 수정");
    teamSelect = createTeamSelect(task.team, "팀 수정");
    teamSelect.hidden = task.visibility !== "TEAM";
    visibilityField.addEventListener("change", () => {
      teamSelect.hidden = visibilityField.value !== "TEAM";
    });
  }

  const save = () => {
    const input = readTaskInput(titleField.value, descriptionField.value, priorityField.value, dueField.value);
    if (owner) {
      const sharing = readSharing(visibilityField.value, teamSelect.value);
      const currentTeamId = task.team ? task.team.id : null;
      // 바뀌었을 때만 보낸다(떠난 팀의 할 일을 그대로 두고 내용만 고칠 수 있게).
      if (sharing.visibility !== task.visibility || sharing.team_id !== currentTeamId) {
        Object.assign(input, sharing);
        if (sharing.visibility === "PRIVATE") {
          delete input.team_id;
        }
      }
    }
    saveEdit(task.id, input);
  };

  titleField.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      save();
    }
  });
  container.addEventListener("keydown", (event) => {
    if (event.key === "Escape") {
      cancelEdit();
    }
  });

  const options = document.createElement("div");
  options.className = "form-row";
  options.appendChild(priorityField);
  options.appendChild(dueField);
  if (owner) {
    options.appendChild(visibilityField);
    options.appendChild(teamSelect);
  }
  options.appendChild(createButton("저장", save));
  options.appendChild(createButton("취소", cancelEdit));

  container.appendChild(titleField);
  container.appendChild(descriptionField);
  container.appendChild(options);
  return { container, focusTarget: titleField };
}

function createBadge(text, className) {
  const badge = document.createElement("span");
  badge.className = `badge ${className}`;
  badge.textContent = text;
  return badge;
}

function createTaskItem(task, today) {
  const item = document.createElement("li");
  item.dataset.id = String(task.id);
  const classes = [];
  if (task.status === "DONE") {
    classes.push("done");
  }
  if (isOverdue(task, today)) {
    classes.push("overdue");
  }
  item.className = classes.join(" ");

  if (task.id === editingId) {
    const { container, focusTarget } = createEditForm(task);
    item.appendChild(container);
    if (editError) {
      const error = document.createElement("p");
      error.className = "form-error";
      error.textContent = editError;
      item.appendChild(error);
    }
    return { item, focusTarget };
  }

  const main = document.createElement("div");
  main.className = "task-main";

  const info = document.createElement("div");
  info.className = "task-info";

  const title = document.createElement("span");
  title.className = "task-title";
  // 사용자 입력은 HTML로 해석하지 않고 글자로만 표시한다.
  title.textContent = task.title;

  const meta = document.createElement("div");
  meta.className = "task-meta";
  meta.appendChild(
    createBadge(labelOf(PRIORITIES, task.priority), `priority-${task.priority.toLowerCase()}`)
  );
  if (task.due_date !== null) {
    meta.appendChild(createBadge(`마감 ${task.due_date}`, "due"));
  }
  meta.appendChild(
    task.visibility === "TEAM" && task.team
      ? createBadge(`팀 ${task.team.name}`, "team")
      : createBadge("개인", "private")
  );
  if (!isOwner(task)) {
    meta.appendChild(createBadge(`작성자 ${task.owner.username}`, "owner"));
  }
  if (isOverdue(task, today)) {
    meta.appendChild(createBadge("지연", "overdue-badge"));
  }

  info.appendChild(title);
  info.appendChild(meta);
  if (task.description !== "") {
    const description = document.createElement("p");
    description.className = "task-description";
    description.textContent = task.description;
    info.appendChild(description);
  }

  const actions = document.createElement("div");
  actions.className = "task-actions";
  actions.appendChild(createStatusSelect(task));
  actions.appendChild(createButton("수정", () => startEdit(task.id)));
  // 삭제는 작성자만 할 수 있다(서버도 403으로 거절한다).
  if (isOwner(task)) {
    actions.appendChild(createButton("삭제", () => deleteTask(task.id)));
  }

  main.appendChild(info);
  main.appendChild(actions);
  item.appendChild(main);
  return { item, focusTarget: null };
}

function render() {
  taskList.replaceChildren();
  const today = todayString();
  let focusTarget = null;

  for (const task of tasks) {
    const created = createTaskItem(task, today);
    taskList.appendChild(created.item);
    if (created.focusTarget) {
      focusTarget = created.focusTarget;
    }
  }

  taskCount.textContent = hasFilters() ? `(검색 결과 ${tasks.length})` : `(${tasks.length})`;
  emptyMessage.hidden = tasks.length > 0;
  if (loadFailed && tasks.length === 0) {
    emptyMessage.textContent = "목록을 불러오지 못했습니다.";
  } else {
    emptyMessage.textContent = hasFilters()
      ? "조건에 맞는 할 일이 없습니다."
      : "등록된 할 일이 없습니다.";
  }
  if (focusTarget && focusEditForm) {
    focusTarget.focus();
  }
  focusEditForm = false;
}

function resetForm() {
  titleInput.value = "";
  descriptionInput.value = "";
  priorityInput.value = DEFAULT_PRIORITY;
  dueInput.value = "";
  visibilityInput.value = "PRIVATE";
  updateTaskTeamField();
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (submitButton.disabled) {
    return;
  }

  const input = {
    ...readTaskInput(titleInput.value, descriptionInput.value, priorityInput.value, dueInput.value),
    ...readSharing(visibilityInput.value, teamInput.value),
  };
  const error = validateTaskInput(input);
  if (error) {
    formError.textContent = error;
    titleInput.focus();
    return;
  }

  // 응답을 기다리는 동안 같은 할 일이 두 번 등록되지 않도록 버튼을 잠근다.
  submitButton.disabled = true;
  try {
    await request("POST", "/tasks", input);
  } catch (requestError) {
    formError.textContent = `등록하지 못했습니다. ${requestError.message}`;
    return;
  } finally {
    submitButton.disabled = false;
  }

  formError.textContent = "";
  resetForm();
  titleInput.focus();
  await loadTasks();
});

searchInput.addEventListener("input", () => {
  filters.query = searchInput.value;
  // 글자를 입력할 때마다 요청하지 않도록 입력이 멈춘 뒤 조회한다.
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(loadTasks, SEARCH_DELAY_MS);
});
statusFilter.addEventListener("change", () => {
  filters.status = statusFilter.value;
  loadTasks();
});
priorityFilter.addEventListener("change", () => {
  filters.priority = priorityFilter.value;
  loadTasks();
});
scopeFilter.addEventListener("change", () => {
  filters.scope = scopeFilter.value;
  loadTasks();
});
visibilityInput.addEventListener("change", updateTaskTeamField);

// ---- 팀 ----

// 내 팀 목록으로 팀 선택 상자를 만든다. 현재 팀이 내 팀이 아니면(팀을 떠난 작성자) 그 팀도 선택지에 넣는다.
function createTeamSelect(currentTeam, ariaLabel) {
  const options = myTeams.map((team) => ({ value: String(team.id), label: team.name }));
  if (currentTeam && !myTeams.some((team) => team.id === currentTeam.id)) {
    options.unshift({ value: String(currentTeam.id), label: `${currentTeam.name} (떠난 팀)` });
  }
  const select = createSelect(options, currentTeam ? String(currentTeam.id) : "", ariaLabel);
  if (!currentTeam && options.length > 0) {
    select.value = options[0].value;
  }
  return select;
}

// 등록 폼: 공개 범위가 팀이면 팀 선택을 보인다. 속한 팀이 없으면 팀을 고를 수 없다.
function updateTaskTeamField() {
  const hasTeams = myTeams.length > 0;
  visibilityInput.querySelector('option[value="TEAM"]').disabled = !hasTeams;
  if (!hasTeams && visibilityInput.value === "TEAM") {
    visibilityInput.value = "PRIVATE";
  }
  teamField.hidden = visibilityInput.value !== "TEAM";
  noTeamHelp.hidden = hasTeams;
}

function fillOptions(select, options, keepValue) {
  const previous = keepValue ? select.value : "";
  select.replaceChildren();
  for (const item of options) {
    const option = document.createElement("option");
    option.value = item.value;
    option.textContent = item.label;
    select.appendChild(option);
  }
  select.value = options.some((item) => item.value === previous) ? previous : options.length ? options[0].value : "";
}

// 팀 목록이 바뀌면 등록 폼의 팀 선택과 범위 필터의 팀 항목을 다시 만든다.
function updateTeamSelects() {
  fillOptions(
    teamInput,
    myTeams.map((team) => ({ value: String(team.id), label: team.name })),
    true
  );
  updateTaskTeamField();
  const scopeOptions = [
    { value: "", label: "범위 전체" },
    { value: "mine", label: "내 할 일" },
    ...myTeams.map((team) => ({ value: `team:${team.id}`, label: `팀: ${team.name}` })),
  ];
  scopeFilter.value = filters.scope;
  fillOptions(scopeFilter, scopeOptions, true);
  filters.scope = scopeFilter.value;
}

async function loadMyTeams() {
  try {
    myTeams = await request("GET", "/teams");
  } catch (error) {
    myTeams = [];
  }
  updateTeamSelects();
}

// 팀 화면: 내 팀과 각 팀의 멤버를 받아 그린다.
async function loadTeamsView() {
  try {
    myTeams = await request("GET", "/teams");
    teamDetails = await Promise.all(
      myTeams.map(async (team) => ({ team, members: await request("GET", `/teams/${team.id}/members`) }))
    );
    teamError.textContent = "";
  } catch (error) {
    teamError.textContent = `팀 목록을 불러오지 못했습니다. ${error.message}`;
  }
  updateTeamSelects();
  renderTeams();
}

async function runTeamAction(teamId, action) {
  teamErrors.delete(teamId);
  try {
    await action();
  } catch (error) {
    teamErrors.set(teamId, error.message);
  }
  await loadTeamsView();
}

function addMember(teamId, username) {
  if (username === "") {
    teamErrors.set(teamId, "추가할 아이디를 입력하세요.");
    renderTeams();
    return Promise.resolve();
  }
  return runTeamAction(teamId, () => request("POST", `/teams/${teamId}/members`, { username }));
}

function removeMember(team, member) {
  const self = member.user.id === currentUser.id;
  const question = self
    ? `"${team.name}" 팀을 떠날까요? 이 팀의 할 일을 더 이상 볼 수 없습니다.`
    : `"${member.user.username}"님을 "${team.name}" 팀에서 제거할까요?`;
  if (!window.confirm(question)) {
    return Promise.resolve();
  }
  return runTeamAction(team.id, () => request("DELETE", `/teams/${team.id}/members/${member.user.id}`));
}

function createTeamItem({ team, members }) {
  const item = document.createElement("li");
  item.dataset.teamId = String(team.id);
  const amOwner = team.owner.id === currentUser.id;

  const header = document.createElement("div");
  header.className = "team-header";
  const name = document.createElement("span");
  name.className = "team-name";
  name.textContent = team.name;
  header.appendChild(name);
  header.appendChild(createBadge(`팀장 ${team.owner.username}`, "owner"));
  header.appendChild(createBadge(`멤버 ${members.length}명`, "count"));
  item.appendChild(header);

  const memberList = document.createElement("ul");
  memberList.className = "member-list";
  for (const member of members) {
    const row = document.createElement("li");
    const memberName = document.createElement("span");
    memberName.className = "member-name";
    memberName.textContent = member.user.username;
    row.appendChild(memberName);
    if (member.is_owner) {
      row.appendChild(createBadge("팀장", "owner"));
    } else if (member.user.id === currentUser.id) {
      row.appendChild(createButton("탈퇴", () => removeMember(team, member)));
    } else if (amOwner) {
      row.appendChild(createButton("제거", () => removeMember(team, member)));
    }
    memberList.appendChild(row);
  }
  item.appendChild(memberList);

  // 멤버 추가는 팀장만 할 수 있다.
  if (amOwner) {
    const addForm = document.createElement("form");
    addForm.className = "form-row member-form";
    addForm.noValidate = true;
    const input = document.createElement("input");
    input.type = "text";
    input.placeholder = "추가할 아이디";
    input.autocomplete = "off";
    input.setAttribute("aria-label", `${team.name} 팀에 추가할 아이디`);
    const button = document.createElement("button");
    button.type = "submit";
    button.textContent = "멤버 추가";
    addForm.appendChild(input);
    addForm.appendChild(button);
    addForm.addEventListener("submit", (event) => {
      event.preventDefault();
      addMember(team.id, input.value.trim());
    });
    item.appendChild(addForm);
  }

  if (teamErrors.has(team.id)) {
    const error = document.createElement("p");
    error.className = "form-error";
    error.setAttribute("role", "alert");
    error.textContent = teamErrors.get(team.id);
    item.appendChild(error);
  }
  return item;
}

function renderTeams() {
  teamList.replaceChildren(...teamDetails.map(createTeamItem));
  teamsEmpty.hidden = teamDetails.length > 0;
}

teamForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (teamButton.disabled) {
    return;
  }
  const name = teamNameInput.value.trim();
  const length = textLength(name);
  if (length < 1 || length > TEAM_NAME_MAX_LENGTH) {
    teamError.textContent = `팀 이름은 1~${TEAM_NAME_MAX_LENGTH}자로 입력하세요.`;
    return;
  }
  teamButton.disabled = true;
  try {
    await request("POST", "/teams", { name });
  } catch (requestError) {
    teamError.textContent = `팀을 만들지 못했습니다. ${requestError.message}`;
    return;
  } finally {
    teamButton.disabled = false;
  }
  teamNameInput.value = "";
  await loadTeamsView();
});

// ---- 로그인·회원가입과 화면 전환 ----

function currentRoute() {
  return ROUTES[window.location.hash] ? window.location.hash : DEFAULT_ROUTE;
}

// 주소를 바꾼다. replace면 뒤로가기 기록을 남기지 않는다(자동 이동에 사용).
function navigate(hash, replace = false) {
  if (window.location.hash === hash) {
    showRoute();
  } else if (replace) {
    window.location.replace(hash);
  } else {
    window.location.hash = hash;
  }
}

function showRoute() {
  const hash = currentRoute();
  const route = ROUTES[hash];
  // 로그인 여부와 맞지 않는 화면이면 맞는 화면으로 보낸다.
  if (route.needsLogin && !currentUser) {
    navigate(WELCOME_ROUTE, true);
    return;
  }
  if (!route.needsLogin && currentUser) {
    navigate(DEFAULT_ROUTE, true);
    return;
  }
  if (window.location.hash !== hash) {
    window.history.replaceState(null, "", hash);
  }

  loadingMessage.hidden = true;
  for (const [name, element] of Object.entries(views)) {
    element.hidden = name !== route.view;
  }
  document.title = `${route.title} - Task Flow`;
  userBar.hidden = !currentUser;
  guestBar.hidden = Boolean(currentUser);
  for (const [name, link] of Object.entries(guestLinks)) {
    if (name === route.view) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }
  currentUsername.textContent = currentUser ? currentUser.username : "";
  for (const [name, link] of Object.entries(navLinks)) {
    if (name === route.view) {
      link.setAttribute("aria-current", "page");
    } else {
      link.removeAttribute("aria-current");
    }
  }

  if (route.view === "welcome") {
    loginNotice.textContent = "";
  } else if (route.view === "login") {
    loginError.textContent = "";
    loginPassword.value = "";
    (loginUsername.value ? loginPassword : loginUsername).focus();
  } else if (route.view === "signup") {
    signupError.textContent = "";
    signupUsername.focus();
  } else if (route.view === "teams") {
    loginNotice.textContent = "";
    loadTeamsView();
  } else {
    loginNotice.textContent = "";
    loadMyTeams().then(loadTasks);
  }
}

// 로그아웃하거나 세션이 끝났을 때 이전 사용자의 화면 상태를 지운다.
function clearUserState() {
  currentUser = null;
  tasks = [];
  editingId = null;
  editError = "";
  loadFailed = false;
  listRequestId += 1;
  window.clearTimeout(searchTimer);
  filters.query = "";
  filters.status = "";
  filters.priority = "";
  filters.scope = "";
  searchInput.value = "";
  statusFilter.value = "";
  priorityFilter.value = "";
  myTeams = [];
  teamDetails = [];
  teamErrors.clear();
  updateTeamSelects();
  teamList.replaceChildren();
  teamNameInput.value = "";
  teamError.textContent = "";
  resetForm();
  formError.textContent = "";
  apiError.textContent = "";
  taskList.replaceChildren();
}

function handleSessionExpired() {
  if (!currentUser) {
    return;
  }
  clearUserState();
  loginNotice.textContent = "로그인이 필요합니다. 다시 로그인하세요.";
  navigate(LOGIN_ROUTE, true);
}

function validateSignup(username, password) {
  if (!USERNAME_PATTERN.test(username)) {
    return "아이디는 영문 소문자·숫자·밑줄 3~30자여야 합니다.";
  }
  const length = textLength(password);
  if (length < PASSWORD_MIN_LENGTH || length > PASSWORD_MAX_LENGTH) {
    return `비밀번호는 ${PASSWORD_MIN_LENGTH}~${PASSWORD_MAX_LENGTH}자여야 합니다.`;
  }
  return null;
}

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (loginButton.disabled) {
    return;
  }
  const username = loginUsername.value;
  const password = loginPassword.value;
  if (username === "" || password === "") {
    loginError.textContent = "아이디와 비밀번호를 입력하세요.";
    return;
  }
  loginButton.disabled = true;
  try {
    currentUser = await request("POST", "/auth/login", { username, password });
  } catch (requestError) {
    loginError.textContent = requestError.message;
    loginPassword.value = "";
    loginPassword.focus();
    return;
  } finally {
    loginButton.disabled = false;
  }
  loginPassword.value = "";
  loginError.textContent = "";
  loginNotice.textContent = "";
  navigate(DEFAULT_ROUTE);
});

signupForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (signupButton.disabled) {
    return;
  }
  // 아이디와 비밀번호는 변환하지 않고 입력한 그대로 보낸다(서버도 같은 규칙으로 검증).
  const username = signupUsername.value;
  const password = signupPassword.value;
  const error = validateSignup(username, password);
  if (error) {
    signupError.textContent = error;
    return;
  }
  signupButton.disabled = true;
  try {
    await request("POST", "/auth/signup", { username, password });
  } catch (requestError) {
    signupError.textContent = requestError.message;
    return;
  } finally {
    signupButton.disabled = false;
  }
  // 가입만 하고 자동 로그인하지 않는다. 로그인 화면에 아이디를 채워 둔다.
  signupForm.reset();
  signupError.textContent = "";
  loginUsername.value = username;
  loginNotice.textContent = "가입되었습니다. 로그인하세요.";
  navigate(LOGIN_ROUTE);
});

logoutButton.addEventListener("click", async () => {
  logoutButton.disabled = true;
  try {
    await request("POST", "/auth/logout");
  } catch (requestError) {
    // 서버에 연결하지 못해도 화면에서는 로그아웃 상태로 바꾼다.
  } finally {
    logoutButton.disabled = false;
  }
  clearUserState();
  loginUsername.value = "";
  navigate(WELCOME_ROUTE);
});

window.addEventListener("hashchange", showRoute);

// 처음 열 때 세션 쿠키로 로그인 상태를 확인한 뒤 화면을 고른다.
async function start() {
  try {
    currentUser = await request("GET", "/auth/me");
  } catch (requestError) {
    currentUser = null;
    if (requestError.status !== 401) {
      loginNotice.textContent = requestError.message;
    }
  }
  showRoute();
}

start();
