import { apiRequest } from "./api.js";
import { EVENT_CATEGORIES, eventCategoryOf } from "./categories.js";
import { formatJapaneseDateWithWeekday, localDateString } from "./dates.js";
import { errorMessageOf, getElement, setVisible } from "./ui.js";

// 一覧表示の期間の日数（今日から4週間）。前後への移動も、この日数ずつ。
const LIST_DAYS = 28;
// 一覧表示の行で、タイトルの横に出す主要項目（カテゴリの保存値 → 予定の項目）。
const LIST_DETAIL_FIELDS = new Map([
  ["class", "room"],
  ["part_time", "employer"],
]);
const LIBRARY_ERROR_MESSAGE =
  "カレンダーの部品を読み込めませんでした。" +
  "ネットワークの接続を確かめて、ページを再読み込みしてください";

let calendar = null;
// 絞り込みで外したカテゴリの保存値。初期状態は、すべてのカテゴリを表示する。
const hiddenCategories = new Set();
// 予定の取得の通し番号。古い取得の結果で、今の表示（エラーの表示）を
// 変えないために使う（古い取得の予定は、FullCalendarが捨てる）。
let requestSerial = 0;

function showLoadError(error) {
  getElement("calendar-load-error-message").textContent =
    errorMessageOf(error);
  setVisible(getElement("calendar-load-error"), true);
}

function hideLoadError() {
  setVisible(getElement("calendar-load-error"), false);
}

// FullCalendarの期間（終わりの日を含まない Date）を、予定APIの期間
// （両端を含む YYYY-MM-DD）にする。終わりの日は、その前の日にする。
function toApiRange(start, end) {
  // 日に0を渡すと、前の月の最後の日になる（月をまたいでも正しい）。
  const lastDate = new Date(
    end.getFullYear(),
    end.getMonth(),
    end.getDate() - 1,
  );
  return {
    startDate: localDateString(start),
    endDate: localDateString(lastDate),
  };
}

// 予定APIの予定を、FullCalendarの予定の形にする。日時は、タイムゾーンの
// ない「YYYY-MM-DDTHH:MM」で渡す（ブラウザのローカルの日時として読まれる）。
function toCalendarEvent(apiEvent) {
  const category = eventCategoryOf(apiEvent.category);
  return {
    id: String(apiEvent.id),
    title: apiEvent.title,
    start: `${apiEvent.date}T${apiEvent.start_time}`,
    end: `${apiEvent.date}T${apiEvent.end_time}`,
    classNames: category.className === "" ? [] : [category.className],
    // 詳細パネルと一覧表示で使うため、APIの予定のコピーを持たせる。
    extendedProps: { apiEvent: { ...apiEvent } },
  };
}

// FullCalendarが、表示する期間が変わるたびと、refetchEvents() のたびに
// 呼ぶ。予定APIから期間の予定を取得し、絞り込みで外したカテゴリを除く。
async function fetchEvents(fetchInfo) {
  requestSerial += 1;
  const serial = requestSerial;
  const { startDate, endDate } = toApiRange(fetchInfo.start, fetchInfo.end);
  const query = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
  });

  let apiEvents;
  try {
    apiEvents = await apiRequest("GET", `/api/events?${query}`);
  } catch (error) {
    if (serial === requestSerial) {
      showLoadError(error);
    }
    // FullCalendarに、取得の失敗を伝える。
    throw error;
  }

  if (serial === requestSerial) {
    hideLoadError();
  }
  return apiEvents
    .filter((apiEvent) => !hiddenCategories.has(apiEvent.category))
    .map(toCalendarEvent);
}

// 一覧表示の行の、タイトルの欄の中身。アイコン・タイトルと、カテゴリごとの
// 主要項目（授業＝教室、アルバイト＝派遣会社）を、textContent で作る。
function renderListEventContent(arg) {
  const apiEvent = arg.event.extendedProps.apiEvent;
  const category = eventCategoryOf(apiEvent.category);

  const icon = document.createElement("span");
  icon.className = "me-1";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = category.icon;

  const title = document.createElement("span");
  title.textContent = apiEvent.title;

  const nodes = [icon, title];
  const detailField = LIST_DETAIL_FIELDS.get(apiEvent.category);
  if (detailField !== undefined && apiEvent[detailField] !== null) {
    const detail = document.createElement("span");
    detail.className = "ms-2 text-muted small";
    detail.textContent = apiEvent[detailField];
    nodes.push(detail);
  }
  return { domNodes: nodes };
}

// 詳細パネルの1行（教室・派遣会社・メモ）。値がなければ、行ごと隠す。
function setDetailRow(rowId, valueId, value) {
  getElement(valueId).textContent = value ?? "";
  setVisible(getElement(rowId), value !== null);
}

// 予定の詳細パネルを開く（読み取りだけ。閉じるのは、利用者のボタンだけ）。
function showEventDetail(apiEvent) {
  const category = eventCategoryOf(apiEvent.category);
  getElement("event-modal-title").textContent = apiEvent.title;
  getElement("event-modal-category-icon").textContent = category.icon;
  getElement("event-modal-category").textContent = category.label;
  getElement("event-modal-date").textContent =
    formatJapaneseDateWithWeekday(apiEvent.date);
  getElement("event-modal-time").textContent =
    `${apiEvent.start_time} 〜 ${apiEvent.end_time}`;
  setDetailRow("event-modal-room-row", "event-modal-room", apiEvent.room);
  setDetailRow(
    "event-modal-employer-row",
    "event-modal-employer",
    apiEvent.employer,
  );
  setDetailRow("event-modal-notes-row", "event-modal-notes", apiEvent.notes);

  const modal = window.bootstrap.Modal.getOrCreateInstance(
    getElement("event-modal"),
  );
  modal.show();
}

// 絞り込みの選択肢を、カテゴリの対応表から作る（表示名を1か所で持つため）。
function renderFilter() {
  const fragment = document.createDocumentFragment();

  for (const [code, category] of Object.entries(EVENT_CATEGORIES)) {
    const item = document.createElement("div");
    item.className = "form-check form-check-inline me-0";

    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.className = "form-check-input";
    checkbox.id = `calendar-filter-${code}`;
    checkbox.checked = true;
    checkbox.addEventListener("change", () => {
      if (checkbox.checked) {
        hiddenCategories.delete(code);
      } else {
        hiddenCategories.add(code);
      }
      // fetchEvents が、今の絞り込みで予定を選び直すように、取得し直す。
      calendar.refetchEvents();
    });

    const label = document.createElement("label");
    label.className = "form-check-label";
    label.htmlFor = checkbox.id;
    const swatch = document.createElement("span");
    swatch.className = `category-swatch ${category.className} me-1`;
    swatch.setAttribute("aria-hidden", "true");
    label.append(swatch, category.label);

    item.append(checkbox, label);
    fragment.append(item);
  }

  getElement("calendar-filter").replaceChildren(fragment);
}

export function initCalendar() {
  // FullCalendarは、base.html の通常のスクリプトで、このファイルより先に
  // 読み込まれる。読み込めなかった場合（ネットワークにつながらないなど）は、
  // ほかのモードを止めないように、例外にせず、メッセージだけを出す。
  if (window.FullCalendar === undefined) {
    getElement("calendar-load-error-message").textContent =
      LIBRARY_ERROR_MESSAGE;
    setVisible(getElement("calendar-retry-button"), false);
    setVisible(getElement("calendar-load-error"), true);
    setVisible(getElement("calendar-content"), false);
    return;
  }

  renderFilter();
  calendar = new window.FullCalendar.Calendar(getElement("calendar-view"), {
    locale: "ja",
    // 日曜始まり
    firstDay: 0,
    initialView: "timeGridWeek",
    headerToolbar: {
      left: "prev,next today",
      center: "title",
      right: "timeGridWeek,dayGridMonth,listFourWeeks",
    },
    // 日本語の文言のファイルは読み込まず、使う文言を、ここで指定する。
    buttonText: { today: "今日", week: "週", month: "月" },
    buttonHints: { prev: "前へ", next: "次へ", today: "今日を表示" },
    viewHint: "$0表示",
    navLinkHint: "$0を含む週を表示",
    moreLinkText: (count) => `＋${count}件`,
    moreLinkHint: (count) => `ほかに${count}件の予定（週の表示へ）`,
    noEventsText: "表示する予定はありません",
    timeHint: "時間",
    eventHint: "予定",
    eventTimeFormat: { hour: "2-digit", minute: "2-digit", hour12: false },
    // 予定は、色のブロックで表示する。月表示の既定の●の印は、期限型の
    // 締切に使うため。この設定は、表示ごと（views）には指定できず、
    // 週表示と一覧表示の見た目は変わらない。
    eventDisplay: "block",
    // 週表示：終日の行は出さない（予定は、すべて時刻を持つ）。時間軸は
    // 0〜24時の全体にし（範囲の外の予定が消えないように）、8時から見せる。
    allDaySlot: false,
    scrollTime: "08:00:00",
    views: {
      dayGridMonth: {
        // 時間型の予定は、時刻を出さず、タイトルだけを表示する。
        displayEventTime: false,
        // 1日3件まで。4件目以降は「＋N件」にまとめる。
        dayMaxEvents: 3,
        // 日付と「＋N件」のクリックで、その日を含む週の週表示へ移る。
        navLinks: true,
        navLinkDayClick: "timeGridWeek",
        moreLinkClick: "timeGridWeek",
      },
      listFourWeeks: {
        type: "list",
        // 日数（days）で指定する。週（weeks）で指定すると、日曜日に
        // そろってしまうため。日数なら、表示中の日付（初めは今日）から始まる。
        duration: { days: LIST_DAYS },
        buttonText: "一覧",
        // 日付の見出しに、曜日を付ける（例：2026年10月13日(火)）。
        listDayFormat: {
          year: "numeric",
          month: "long",
          day: "numeric",
          weekday: "short",
        },
        eventContent: renderListEventContent,
      },
    },
    events: fetchEvents,
    // 取得の失敗は、fetchEvents が画面に出す。FullCalendarの既定の、
    // コンソールへの警告は出さない。
    eventSourceFailure: () => {},
    loading: (isLoading) => {
      setVisible(getElement("calendar-loading"), isLoading);
    },
    eventClick: (info) => {
      showEventDetail(info.event.extendedProps.apiEvent);
    },
  });

  getElement("calendar-retry-button").addEventListener("click", () => {
    calendar.refetchEvents();
  });
  getElement("calendar-tab").addEventListener("shown.bs.tab", () => {
    // ほかのモードでの登録（授業・休講日など）を反映するため、カレンダーの
    // モードを開くたびに、予定を取得し直す。隠れている間に画面の幅が
    // 変わった場合に備えて、大きさも計算し直す。
    calendar.updateSize();
    calendar.refetchEvents();
  });
  calendar.render();
}
