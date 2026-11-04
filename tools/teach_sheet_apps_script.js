// Google Apps Script for the shared "taught barcodes" sheet used by Cena Checker.
// Paste into Extensions > Apps Script of a new Google Sheet, then
// Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
// Put the resulting /exec URL into TEACH_URL in docs/app.js.
//
//   POST {ean, name, shop} -> appends a PENDING row (time, ean, name, shop, approved checkbox)
//   GET                    -> {rows: [{ean, name}]} APPROVED rows only, for thu_ma_day.py
//
// Review: tick "approved" to accept a row, delete the row to reject it. Only ticked rows reach
// the website (next daily data update). Unticking or deleting a row removes it again.

function sheet_() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  if (sh.getLastRow() === 0) sh.appendRow(['time', 'ean', 'name', 'shop', 'approved']);
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
    var sh = sheet_();
    var v = sh.getDataRange().getValues();
    for (var i = 1; i < v.length; i++) {           // same code + item already listed -> skip
      if (String(v[i][1]) === ean && String(v[i][2]) === name) return json_({ ok: true });
    }
    // leading apostrophe keeps the barcode as text (no 4.06E+12)
    sh.appendRow([new Date(), "'" + ean, name, String(d.shop || '').slice(0, 60), false]);
    sh.getRange(sh.getLastRow(), 5).insertCheckboxes();
  } finally {
    lock.releaseLock();
  }
  return json_({ ok: true });
}

function doGet() {
  var v = sheet_().getDataRange().getValues().slice(1);
  return json_({ rows: v.filter(function (r) { return r[4] === true; })
    .map(function (r) { return { ean: String(r[1]), name: String(r[2]) }; }) });
}
