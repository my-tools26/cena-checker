// Google Apps Script for the shared "taught barcodes" sheet used by Cena Checker.
// Paste into Extensions > Apps Script of a new Google Sheet, then
// Deploy > New deployment > Web app (Execute as: Me, Who has access: Anyone).
// Put the resulting /exec URL into TEACH_URL in docs/app.js.
//
//   POST {ean, name, price, weight, origin, shop} -> appends a PENDING row. name + price required.
//                             Each barcode only once: repeat -> {dup: 'pending' | 'approved'}
//   GET                    -> {rows: [{ean, name, price, weight, origin}]} APPROVED rows only,
//                             for thu_ma_day.py
//
// Review: tick "approved" to accept a row, delete the row to reject it. Only ticked rows reach
// the website (next daily data update). Unticking or deleting a row removes it again.

var HEAD_ = ['time', 'ean', 'name', 'price', 'weight', 'origin', 'shop', 'approved'];

function sheet_() {
  var sh = SpreadsheetApp.getActiveSpreadsheet().getSheets()[0];
  if (sh.getRange(1, 8).getValue() !== 'approved') sh.getRange(1, 1, 1, 8).setValues([HEAD_]);
  return sh;
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

// Public input: a leading = + - @ would run as a spreadsheet formula -> force plain text
function txt_(v, n) {
  var s = String(v || '').trim().slice(0, n);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function doPost(e) {
  var d;
  try { d = JSON.parse(e.postData.contents); } catch (err) { return json_({ ok: false }); }
  var ean = String(d.ean || '').replace(/\D/g, '');
  var name = txt_(d.name, 200);
  var price = Number(String(d.price || '').replace(',', '.'));
  if (ean.length < 8 || ean.length > 14 || !name || !(price > 0 && price < 100000)) {
    return json_({ ok: false });
  }
  var lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    var sh = sheet_();
    var v = sh.getDataRange().getValues();
    for (var i = 1; i < v.length; i++) {           // each barcode only once, whatever the item
      if (String(v[i][1]) === ean) return json_({ dup: v[i][7] === true ? 'approved' : 'pending' });
    }
    // leading apostrophe keeps the barcode as text (no 4.06E+12)
    sh.appendRow([new Date(), "'" + ean, name, price, txt_(d.weight, 30), txt_(d.origin, 60),
                  txt_(d.shop, 60), false]);
    sh.getRange(sh.getLastRow(), 8).insertCheckboxes();
  } finally {
    lock.releaseLock();
  }
  return json_({ ok: true });
}

function doGet() {
  var v = sheet_().getDataRange().getValues().slice(1);
  return json_({ rows: v.filter(function (r) { return r[7] === true; }).map(function (r) {
    return { ean: String(r[1]), name: String(r[2]), price: r[3], weight: String(r[4]),
             origin: String(r[5]) };
  }) });
}
