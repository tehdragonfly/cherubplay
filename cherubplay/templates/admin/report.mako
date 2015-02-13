<%inherit file="../base.mako" />\
<%def name="render_report(report, detail=True)">\
      <h3>#${report.id}: <a href="${request.route_path("admin_user", username=report.reporting_user.username)}">${report.reporting_user.username}</a> reported <a href="${request.route_path("admin_user", username=report.reported_user.username)}">${report.reported_user.username}</a></h3>
      <p class="subtitle">${report.created.strftime("%a %d %b %Y, %H:%M")}</p>
% if detail:
      <p>Status: <select name="status">
% for value in PromptReport.status.type.enums:
        <option value="${value}"${" selected=\"selected\"" if report.status == value else ""|n}>${value.capitalize()}</option>
% endfor
      </select> <button type="submit">Save</button></p>
% endif
      <p>Posted in ${prompt_categories[report.category]}, ${prompt_levels[report.level]}</p>
      <p style="color: #${report.colour};">Prompt: \
% if not detail and len(report.prompt)>250:
${report.prompt[:250]}...\
% else:
${report.prompt}\
% endif
</p>
      <p>Reason: \
% if report.reason == "wrong_category":
Should be in ${prompt_categories[report.reason_category]}, ${prompt_levels[report.reason_level]}\
% elif report.reason == "spam":
Spam\
% elif report.reason == "stolen":
Stolen\
% elif report.reason == "multiple":
Posted multiple times\
% elif report.reason == "advert":
Advertising\
% elif report.reason == "ooc":
Soliciting real life or out-of-character interactions\
% endif
</p>\
% if not detail and report.notes:
      <p class="notes">Notes: ${report.notes}</p>
% endif
</%def>\
<%block name="title">#${report.id} - Prompt reports - </%block>
  <h2>Prompt reports</h2>
  <nav id="subnav">
    <section class="tile">
      <h3>Status</h3>
      <ul>
        <li><a href="${request.route_path("admin_report_list")}">Open</a></li>
        <li><a href="${request.route_path("admin_report_list_closed")}">Closed</a></li>
        <li><a href="${request.route_path("admin_report_list_invalid")}">Invalid</a></li>
      </ul>
    </section>
  </nav>
% if request.environ["REQUEST_METHOD"]=="POST":
  <p>Your changes have been saved.</p>
% endif
  <form action="${request.route_path("admin_report", id=request.matchdict["id"])}" method="post">
    <section class="tile">
${render_report(report)}
    </section>
    <section class="tile">
      <h3>Notes</h3>
      <p><textarea id="chat_notes_notes" class="notes" name="notes" placeholder="Notes..." rows="5">${report.notes}</textarea></p>
      <button type="submit">Save</button>
    </section>
  </form>
  <p><a href="${request.route_path("admin_report_list")}">Back to reports</a></p>
