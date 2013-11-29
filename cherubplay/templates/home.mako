<%inherit file="base.mako" />\
  <section id="connecting">
    <h2>Connecting...</h2>
    <noscript>
      <p>It seems you have Javascript disabled. Searching requires Javascript, so you'll need to enable it or swich to a different browser in order to find a roleplaying partner.</p>
    </noscript>
  </section>
  <section id="answer_mode">
    <h2>Answer mode</h2>
    <p>The following people are searching for chats. Answer one of the prompts below or switch to prompt mode to input your own prompt.</p>
    <p><button class="prompt_button">Switch to prompt mode</button></p>
    <ul id="prompt_list"></ul>
  </section>
  <section id="prompt_mode">
    <h2>Prompt mode</h2>
    <p>Enter a prompt below, and other people will be able to see it and answer if they're interested. Alternatively you can see and respond to other people's prompts in answer mode.</p>
    <form class="tile">
      <p>
        <input type="color" id="prompt_colour" size="6" value="#000000" maxlength="7">
        <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select>
      </p>
      <p><textarea id="prompt_text" placeholder="Enter your prompt..."></textarea></p>
      <button type="submit">Search</button>
    </form>
    <p><button class="answer_button">Switch to answer mode</button></p>
  </section>
  <section id="wait_mode">
    <h2>Waiting for an answer</h2>
    <p>Your prompt has been posted. Please wait for an answer.</p>
    <p><button class="prompt_button">Edit prompt</button> <button class="answer_button">Switch to answer mode</button></p>
  </section>
  <section id="connection_error">
    <h2>Connection error</h2>
    <p>The connection to the server has been lost. Please refresh the page to try again.</p>
  </section>
  <script src="http://code.jquery.com/jquery-2.0.3.min.js"></script>
  <script src="/static/home.js"></script>
