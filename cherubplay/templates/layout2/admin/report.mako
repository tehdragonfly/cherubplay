<%inherit file="../base.mako" />\
<%block name="title">#${request.context.id} - Prompt reports - </%block>
<%block name="body_class">layout2</%block>
<%def name="render_report(report, detail=True)">\
        <h3>\
% if detail:
#${report.id}\
% else:
<a href="${request.route_path("admin_report", id=report.id)}">#${report.id}</a>\
% endif
: <a href="${request.route_path("admin_user", username=report.reporting_user.username)}">${report.reporting_user.username}</a> reported <a href="${request.route_path("admin_user", username=report.reported_user.username)}">${report.reported_user.username}</a></h3>
        <p class="subtitle">${request.user.localise_time(report.created).strftime("%a %d %b %Y, %H:%M")}</p>
% if detail:
        <p>Status: <select name="status">
% for value in PromptReport.status.type.enums:
          <option value="${value}"${" selected=\"selected\"" if report.status == value else ""|n}>${value.capitalize()}</option>
% endfor
        </select> <button type="submit">Save</button></p>
% endif
        <p>Posted in ${prompt_categories[report.category]}, ${prompt_levels[report.level]}</p>
        % if detail or len(report.prompt) <= 250:
        <p style="color: #${report.colour};">${report.prompt}</p>
        % else:
        <div class="expandable">
          <a class="toggle" href="${request.route_path("admin_report", id=report.id)}">(more)</a>
          <p class="expanded_content" style="color: #${report.colour};" data-href="${request.route_path("admin_report_ext", ext="json", id=report.id)}" data-type="prompt_report"></p>
          <p class="collapsed_content" style="color: #${report.colour};">${report.prompt[:250]}...</p>
        </div>
        % endif
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
<h2>Prompt reports</h2>
<main class="flex">
  <div class="side_column">
    <nav>
      <h3>Status</h3>
      <ul>
% if request.matched_route.name == "admin_report_list":
        <li>Open</li>
% else:
        <li><a href="${request.route_path("admin_report_list")}">Open</a></li>
% endif
% if request.matched_route.name == "admin_report_list_closed":
        <li>Closed</li>
% else:
        <li><a href="${request.route_path("admin_report_list_closed")}">Closed</a></li>
% endif
% if request.matched_route.name == "admin_report_list_invalid":
        <li>Invalid</li>
% else:
        <li><a href="${request.route_path("admin_report_list_invalid")}">Invalid</a></li>
% endif
      </ul>
    </nav>
  </div>
  <div class="side_column"></div>
  <div id="content">
% if request.environ["REQUEST_METHOD"]=="POST":
    <p>Your changes have been saved.</p>
% endif
    <form action="${request.route_path("admin_report", id=request.matchdict["id"])}" method="post">
      <section class="tile2">
${render_report(request.context)}
      </section>
      <section class="tile2">
        <h3>Notes</h3>
        <p><textarea id="chat_notes_notes" class="notes" name="notes" placeholder="Notes..." rows="5">${request.context.notes}</textarea></p>
        <button type="submit">Save</button>
      </section>
    </form>
    <p><a href="${request.route_path("admin_report_list")}">Back to reports</a></p>
  </div>
</main>
