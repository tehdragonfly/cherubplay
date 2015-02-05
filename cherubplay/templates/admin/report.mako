<%inherit file="../base.mako" />\
<%block name="title">#${report.id} - Prompt reports - </%block>
% if request.environ["REQUEST_METHOD"]=="POST":
  <p>Your changes have been saved.</p>
% endif
  <div class="tile">
  <h3>#${report.id}: <a href="${request.route_path("admin_user", username=report.reporting_user.username)}">${report.reporting_user.username}</a> reported <a href="${request.route_path("admin_user", username=report.reported_user.username)}">${report.reported_user.username}</a></h3>
    <p>Category: ${prompt_categories[report.category]}</p>
    <p style="color: #${report.colour};">Prompt: ${report.prompt}</p>
    <p>Reason: ${report.reason}</p>
    <form action="${request.route_path("admin_report", id=request.matchdict["id"])}" method="post">
      <p><textarea id="chat_notes_notes" class="notes" name="notes" placeholder="Notes..." rows="5">${report.notes}</textarea></p>
      <button type="submit">Save</button>
    </form>
  </div>
  <p><a href="${request.route_path("admin_report_list")}">Back to reports</a></p>
