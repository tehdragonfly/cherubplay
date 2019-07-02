<%! from cherubplay.models.enums import TagType %>\
<%def name="tag_li(tag)">\
<li${" class=\"warning\"" if tag.type == TagType.warning else ""|n}>${tag.name}</li>\
</%def>\
<!DOCTYPE html>
<html>
<head>
<title>Your requests - Cherubplay</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#393">
<link rel="stylesheet" href="../cherubplay2.css">
</head>
<body class="layout2">

<header>
  <h1><img src="../logo.png" alt="Cherubplay"></h1>
</header>

<h2>Your requests</h2>

<main class="flex">
  <div id="content">
    <section class="tile2 request ${rq.status}">
      % if rq.status not in ("posted", "locked"):
        <div class="status">${rq.status.capitalize()}</div>
      % endif
      <% tags_by_type = rq.tags_by_type() %>
      <ul class="request_tags">
        % for tag in tags_by_type[TagType.maturity]:
        ${tag_li(tag)}
        % endfor
        % for tag in tags_by_type[TagType.warning]:
        ${tag_li(tag)}
        % endfor
        % for tag in tags_by_type[TagType.type]:
        ${tag_li(tag)}
        % endfor
      </ul>
      % if tags_by_type[TagType.fandom] or tags_by_type[TagType.character] or tags_by_type[TagType.gender]:
      <h3>Playing:</h3>
      <ul class="request_tags">
        % for tag in tags_by_type[TagType.fandom]:
        ${tag_li(tag)}
        % endfor
        % for tag in tags_by_type[TagType.character]:
        ${tag_li(tag)}
        % endfor
        % for tag in tags_by_type[TagType.gender]:
        ${tag_li(tag)}
        % endfor
      </ul>
      % endif
      % if tags_by_type[TagType.fandom_wanted] or tags_by_type[TagType.character_wanted] or tags_by_type[TagType.gender_wanted]:
      <h3>Looking for:</h3>
      <ul class="request_tags">
        % for tag in tags_by_type[TagType.fandom_wanted]:
        ${tag_li(tag)}
        % endfor
        % for tag in tags_by_type[TagType.character_wanted]:
        ${tag_li(tag)}
        % endfor
        % for tag in tags_by_type[TagType.gender_wanted]:
        ${tag_li(tag)}
        % endfor
      </ul>
      % endif
      % if tags_by_type[TagType.misc]:
      <h3>Other tags:</h3>
      <ul class="request_tags">
        % for tag in tags_by_type[TagType.misc]:
        ${tag_li(tag)}
        % endfor
      </ul>
      % endif
      % if rq.ooc_notes.raw:
        <hr>
        <div class="message">${rq.ooc_notes.as_html()}</div>
      % endif
      % if rq.starter.raw:
        <hr>
        <div class="message" style="color: #${rq.colour};">${rq.starter.as_html()}</div>
      % endif
      <hr>
      % if rq.slots:
        % for slot in rq.slots:
          <label class="slot${slot.order}">
            Slot ${slot.order}
            % if slot.user_id == user.id:
              - taken by you
            % elif slot.taken:
              - taken by ${slot.user_name}
            % endif
          </label>
          <p class="slot_description ${"taken" if slot.taken else ""}">
            ${slot.description}
          </p>
          <hr>
        % endfor
      % endif
      <div class="actions">
        <div class="left">${user.localise_time(rq.posted or rq.created).strftime("%Y-%m-%d %H:%M")}</div>
      </div>
    </section>
  </div>
</main>

</body>
</html>