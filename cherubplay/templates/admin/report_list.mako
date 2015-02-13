<%inherit file="../base.mako" />\
<%block name="title">Prompt reports - </%block>
  <h2>Prompt reports</h2>
% if len(reports)==0:
  <p>No reports. <a href="${request.route_path("home")}">Try shitposting until the users decide they're fed up with you</a>.</p>
% else:
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
  <ul id="chat_list">
% for report in reports:
    <li class="tile">
      <h3><a href="${request.route_path("admin_report", id=report.id)}">#${report.id}</a>: <a href="${request.route_path("admin_user", username=report.reporting_user.username)}">${report.reporting_user.username}</a> reported <a href="${request.route_path("admin_user", username=report.reported_user.username)}">${report.reported_user.username}</a></h3>
      <p class="subtitle">${report.created.strftime("%a %d %b %Y, %H:%M")}</p>
      <p>Posted in ${prompt_categories[report.category]}, ${prompt_levels[report.level]}</p>
      <p style="color: #${report.colour};">Prompt: \
% if len(report.prompt)>250:
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
</p>
% if report.notes!="":
      <p class="notes">Notes: ${report.notes}</p>
% endif
    </li>
% endfor
  </ul>
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
% endif
