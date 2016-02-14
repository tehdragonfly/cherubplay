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
        <form action="${request.route_path("admin_report", id=report.id)}" method="post">
          Set status:
          % for value in PromptReport.status.type.enums:
          % if value != "duplicate":
          % if not loop.first:
          ·
          % endif
          <input type="submit" name="status_${value}" value="${value.capitalize()}"${" disabled=\"disabled\"" if report.status == value else ""}>
          % endif
          % endfor
        </form>
        % if error == "no_report":
        <p class="error">This report ID isn't valid.</p>
        % endif
        % if report.duplicate_of_id:
        <p>Duplicate of <a href="${request.route_path("admin_report", id=report.duplicate_of_id)}">#${report.duplicate_of_id}</a>.</p>
        % else:
        <form action="${request.route_path("admin_report", id=report.id)}" method="post">
          <input type="hidden" name="status_duplicate" value="on">
          <p>Duplicate of #<input type="text" name="duplicate_of_id" size="5"\
% if report.duplicate_of_id:
 value="${report.duplicate_of_id}"
% endif
> <button type="submit">Save</button></p>
        </form>
        % endif
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
    <section class="tile2">
${render_report(request.context)}
    </section>
    <form class="tile2" action="${request.route_path("admin_report", id=request.context.id)}" method="post">
        <h3>Notes</h3>
        <p><textarea id="chat_notes_notes" class="notes" name="notes" placeholder="Notes..." rows="5">${request.context.notes}</textarea></p>
        <div class="actions">
          <div class="right">
            <input type="submit" name="save" value="Save"> ·
            <input type="submit" name="status_closed" value="Save and close"> ·
            <input type="submit" name="status_invalid" value="Save as invalid">
          </div>
        </div>
    </form>
    <p><a href="${request.route_path("admin_report_list")}">Back to reports</a></p>
  </div>
</main>
