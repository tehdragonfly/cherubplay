<%inherit file="../base.mako" />\
<%namespace name="report_base" file="report.mako" />\
<%block name="title">Prompt reports - </%block>
  <h2>Prompt reports</h2>
  <nav id="subnav">
    <section class="tile">
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
    </section>
  </nav>
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
${report_base.render_report(report, False)}
    </li>
% endfor
  </ul>
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
% endif
