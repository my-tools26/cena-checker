// Google Apps Script for the shared "taught barcodes" sheet used by Cena Checker.
// Paste into Extensions > Apps Script of a new Google Sheet, then
// Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
// Put the resulting /exec URL into TEACH_URL in docs/app.js.
//
//   POST {ean, name, shop}  -> appends a row (time, ean, name, shop)
//   GET  ?ean=<code>        -> {name} of the newest row for that code (live lookup on scan)
//   GET  (no params)        -> {rows: [{ean, name}]} for thu_ma_day.py (daily merge)
//
// To fix a wrong entry: delete the row in the sheet, or teach the code again (newest row wins).

function sheet_() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  if (sh.getLastRow() === 0) sh.appendRow(['time', 'ean', 'name', 'shop']);
  return sh;
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

function doPost(e) {
  var d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false }); }
  var ean = String(d.ean || '').replace(/\D/g, '');
  var name = String(d.name || '').trim().slice(0, 200);
  if (ean.length < 8 || ean.length > 14 || !name) return json_({ ok: false });
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    // leading apostrophe keeps the barcode as text (no 4.06E+12)
    sheet_().appendRow([new Date(), "'" + ean, name, String(d.shop || '').slice(0, 60)]);
  } finally {
    lock.releaseLock();
  }
  return json_({ ok: true });
}

function doGet(e) {
  var v = sheet_().getDataRange().getValues().slice(1);
  var want = e && e.parameter && e.parameter.ean ? String(e.parameter.ean).replace(/\D/g, '') : '';
  if (want) {
    for (var i = v.length - 1; i >= 0; i--) {
      if (String(v[i][1]) === want) return json_({ name: String(v[i][2]) });
    }
    return json_({ name: null });
  }
  return json_({ rows: v.map(function (r) { return { ean: String(r[1]), name: String(r[2]) }; }) });
}
