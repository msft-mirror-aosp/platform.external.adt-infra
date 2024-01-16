<?xml version="1.0" encoding="UTF-8" ?>
<!-- A very basic self contained html page that displays the tests. -->
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match="testsuite">
        <html>
            <head>
                <title> Test Results For
                    <xsl:value-of select="@name"/>
                </title>
                <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet" />
                <style>
body {
        background: #ffffff;
        color: #000000;
        font-size: 13px;
        font-family: Verdana, Arial, Helvetica, sans-serif;
        font-size: 12px;
        text-align: justify;
}
h1 { font-size: 30px; }
h2 { font-size: 20px; }
h3 { font-size: 16px; }
h4 { font-size: 12px; font-style: bold;}
dt { font-style: italic; }

pre {
        border: solid #0000ff 1px;
        color: #000000;
        white-space: pre-wrap;       /* css-3 */
        white-space: -moz-pre-wrap;  /* Mozilla, since 1999 */
        white-space: -pre-wrap;      /* Opera 4-6 */
        white-space: -o-pre-wrap;    /* Opera 7 */
        word-wrap: break-word;       /* Internet Explorer 5.5+ */
        background-color: #ffffd0;
        padding-left: 10px;
        padding-right: 10px;
        padding-top: 10px;
        padding-bottom: 10px;
        margin-top: 0px;
        text-align: left;
        margin-left: auto;
        margin-right: auto;
        font-family:    Courier,Monospace, Courier, MS Courier New, Prestige, Everson Mono;
        font-style: normal;
        font-size: 14;
}


/* Scapy default color theme */

span.prompt { color: #0000ff; font-weight: bold; }
span.not_printable { color: #a0a0a0; }
span.layer_name { color: #ff0000; font-weight: bold; }
span.field_name { color: #0000ff; }
span.field_value { color: #ff00ff; }
span.emph_field_name { color: #0000ff; font-weight: bold; text-decoration: underline }
span.emph_field_value { color: #ff00ff; font-weight: bold; text-decoration: underline }
span.packetlist_name { color: #ff0000; font-weight: bold; }
span.packetlist_proto { color: #0000ff; }
span.packetlist_value { color: #ff00ff; }
span.fail { color: #ff0000; font-weight: bold; }
span.success { color: #0000ff; font-weight: bold; }
span.even { color: #000000; font-weight: bold; }
span.odd { color: #000000; }
span.opening { color: #00ffff; }
span.active { color: #000000; }
span.closed { color: #808080; }


.num    { color:#2928ff; }
.esc    { color:#830000; }
.str    { color:#c00000; }
.dstr   { color:#818100; }
.slc    { color:#838183; font-style:italic; }
.com    { color:#838183; font-style:italic; }
.dir    { color:#ff0000; }
.sym    { color:#000000; }
.line   { color:#555555; }
.blue   { color:#0000ff; font-style:italic; }
.kwa    { color:#000000; font-weight:bold; }
.kwb    { color:#00a000; }
.kwc    { color:#00a000; }

.pass {background-color: #ffffff; color: #008900;}
.fail {background-color: #ffffff; color: #bd2121;}
.error {background-color: #ffffff; color: #720808;}
.skip {background-color: #ffffff; color: #d1c10f;}

li.passed {color: #002000; margin-left: 25px;}
li.failed {color: #200000; margin-left: 25px;}
li.skipped {margin-left: 25px;}
span.comment { color:#000000; font-style: italic;}

span.crc {
            font-family: monospace;
            font-size: 12px;
            font-weight: normal;
            margin-top: 10px;
            background-color: #ccccff;
}

span.buttonskip {
            font-family: monospace;
            margin-top: 10px;
            border: 1px solid #aaa;
            padding: 0 2px;
            margin-right: 2px;
            background-color: #ffffaa;
            cursor: pointer;
}
span.buttonpassed {
            font-family: monospace;
            margin-top: 10px;
            background-color: #aaffaa;
            border: 1px solid #aaa;
            padding: 0 2px;
            margin-right: 2px;
            cursor: pointer;
}
span.buttonfailed {
        font-family: monospace;
        margin-top: 10px;
        background-color: #ffaaaa;
        border: 1px solid #aaa;
        padding: 0 2px;
        margin-right: 2px;
        cursor: pointer;
}
span.buttonerror {
        font-family: monospace;
        margin-top: 10px;
        background-color: #dd5d5d;
        border: 1px solid #aaa;
        padding: 0 2px;
        margin-right: 2px;
        cursor: pointer;
}

/* New properties used in the containers that display the attachments */

ul.attachments {
    list-style-type: none; /* Remove bullets */
    padding: 0; /* Remove padding */
    margin: 0; /* Remove margins */
    margin-top: 3px;
}

li.attachment {
    margin-left: 25px;
    padding: 1px;
    font-size: 13px;
    line-height: 1.42857143;
    color: #333;
}

li.attachment::marker {
    content: "\f0c6   ";
    font-family: FontAwesome;
}

a.header {
    margin-left: 5px;
    color: #004a6a;
    font-size: 13px;
    line-height: 1.42857143;
}

li.collapsable {
    margin-left: 10px;
    padding: 1px;
    font-size: 13px;
    line-height: 1.42857143;
    color: #333;
    cursor: pointer;
}

.embedding {
    background-color: #fff;
    overflow: auto;
    margin-left: 17px;
    margin-bottom: 10px;
    border: solid 1px #ddd;
    display: inline-block;
    float: left;
    resize: both;
    max-width: 90vw;
}

.text-box {
    text-align: left;
    margin: 0 1px;
    font-size: 13px;
    overflow-x: auto;
    line-height: 1.42857143;
    color: #bd0a2b;
    white-space: pre-wrap;
    word-wrap: break-word;
    background-color: #fff0f0;
    border: 0px solid #bbb;
}

.text-box-passed {
    text-align: left;
    font-size: 13px;
    overflow-x: auto;
    overflow-y: auto;
    line-height: 1.42857143;
    color: #2E7D32;
    <!-- white-space: pre-wrap; -->
    white-space: pre-wrap;
    word-wrap: break-word;
    background-color: #EEEEEE;
    border: 0px solid #ccc;
    max-width: 100%;
    max-height: 600px;
}

.skip-text {
    text-align: left;
    border: 0px;
    border: solid 1px #ddd;
    margin-left: 17px;
    font-size: 13px;
    overflow-x: auto;
    overflow-y: auto;
    white-space: pre-wrap;
    background-color: #fff3cd;
    color: #333;
    padding: 12.5 30 10 10;
    width: max-content;
}

.image-box {
    height:600px;
}

.img {
    max-height: 600px;
    display: inline-block;
    visibility: visible;
}


.xml-txt {
    display: none;
    overflow: auto;
    border: 1px solid #DDDDDD;
    border-radius: 4px 0 4px 0;
    white-space: pre;
    height: 40em;
    padding: 15 10px;
    max-width: max-content;
    resize: both;
    width: unset;
}


                </style>
                <script language="JavaScript">

function toggle(container, inner_type) {
    var icon = container.querySelector("icon");
    var contents = container.getElementsByClassName("contents")[0];
    var inner = container.getElementsByClassName(inner_type)[0];

    // toggling icon
    if (icon != undefined) {
        icon.classList.toggle('fa-angle-right');
        icon.classList.toggle('fa-angle-down');
    }

    // toggling contents
   if (contents.style.display === "none") {
        contents.style.display = "block";
        inner.style.display = "block";
    } else {
        contents.style.display = "none";
        inner.style.display = "none";
    }
}

/**
 * Extract the testcase logcat from the class logcat
 * @param {string} filename - logcat (class) filename
 * @param {string} testname - testcase name
 */
async function extractLogcat(filename, testname) {

    const currentUrl = window.location.href;
    const currentPath = currentUrl.substring(0, currentUrl.lastIndexOf('/') + 1);
    const logcatUrl = currentPath + filename;

    try {
        // Fetch the content from the provided URL
        const response = await fetch(logcatUrl);

        if (!response.ok) {
            console.error('Failed to fetch the filepath.');
            return '';
        }

        // Read the content from the response
        const fileContent = await response.text();

        // Find the indexes of the start and ending lines
        const startTag = 'TestRunner: started: ' + testname;
        const endTag = 'TestRunner: finished: ' + testname;
        const startIndex = fileContent.lastIndexOf(startTag);
        const startLineIndex = fileContent.lastIndexOf('\n', startIndex) + 1;
        const endIndex = fileContent.indexOf(endTag, startIndex);
        const endLineIndex = fileContent.indexOf('\n', endIndex);

        // Check if both start and end lines are found
        if (startLineIndex === -1 || endLineIndex === -1) {
            console.error('Start or end tag not found in the logcat file.');
            return '';
        }

        const extractedContent = fileContent.slice(startLineIndex, endLineIndex);

        return extractedContent;

    } catch (error) {
        console.error('Error during fetch:', error.message);
        return '';
    }

}

/**
 * Toggle the state of a button of passed class
 * @param {HTMLElement} container - parent HTML container
 * @param {string} id - test number id
 */
async function toggleButtonPassed(container, id) {

    var icons_text = container.querySelectorAll('.icon_txt');
    icons_text.forEach(function(status) {
        status.textContent = (status.textContent === '+') ? '-' : '+';
    });

    var text = document.getElementById('text-' + id);
    if (text !== null) {
        // loading/hiding contents
        if (text.style.display === "none") {
            text.style.display = "block";
        } else {
            text.style.display = "none";
        }
    }
}

function make_visible(elt) { elt.style.visibility='visible'; elt.style.position='relative';
}

function make_hidden(elt) { elt.style.visibility='hidden'; elt.style.position='absolute';
}

function hide(id) {
    make_hidden(document.getElementById(id+'-')); // '-' class placeholder
    make_visible(document.getElementById(id+'+')); // '+' class placeholder
    make_hidden(document.getElementById(id)); // stores the actual test container contents
}

function show(id) {
    make_visible(document.getElementById(id+'-'))
    make_hidden(document.getElementById(id+'+'))
    make_visible(document.getElementById(id))
}

function goto_id(id) {
    document.body.scrollTop = document.getElementById(id).offsetTop;
}

                </script>
            </head>
            <body onload="embed_attachments()">
                <h1 style="text-align: left">Test Results for:
                    <xsl:value-of select="@name"/>
                </h1>
                <strong>
                    <p>
                        TOTAL=&#160;<xsl:value-of select="@tests"/>&#160;,
                        <font class="pass">PASSED=&#160;<xsl:value-of select="@tests - @failures - @errors - @skipped"/>&#160;</font>,
                        <font class="fail">FAILED=&#160;<xsl:value-of select="@failures"/>&#160;</font>,
                        <font class="error">ERRORS=&#160;<xsl:value-of select="@errors"/>&#160;</font>,
                        <font class="skip">SKIPPED=&#160;<xsl:value-of select="@skipped"/>&#160;</font>
                    </p>
                </strong>
                <!-- SUMMARY SQUARES SECTION -->
                <xsl:for-each select="testcase">
                    <xsl:variable name="id" select="position()"/>
                    <xsl:variable name="fid" select=" format-number($id, '000')"/>
                    <xsl:variable name="buttonclass">
                        <xsl:choose>
                            <xsl:when test="failure">buttonfailed</xsl:when>
                            <xsl:when test="error">buttonerror</xsl:when>
                            <xsl:when test="skipped">buttonskip</xsl:when>
                            <xsl:otherwise>buttonpassed</xsl:otherwise>
                        </xsl:choose>
                    </xsl:variable>
                    <span class="{$buttonclass}" onClick="goto_id('tst{$id}l')">
                        <xsl:value-of select="$fid"/>
                    </span>&#160;
                </xsl:for-each>
                <h3 style="margin: 20 0 0 0">
                    <font style="color: red">
                        <span style="margin-right: 3px">API: </span>
                        <xsl:value-of select="substring-before(//testsuites/properties/property[@name='device']/@value,'(AVD)')"/>
                    </font>
                </h3>
                <!-- Ignored Tests Section -->
                <div style="margin-top: 30px;">
                    <h2>Ignored tests (<xsl:value-of select="count(testcase/skipped)"/>)</h2>
                    <ul>
                        <xsl:for-each select="testcase">
                        <xsl:variable name="id" select="position()"/>
                        <xsl:variable name="fid" select=" format-number($id, '000')"/>
                            <xsl:choose>
                                <xsl:when test="skipped">
                                    <li>
                                <span class="buttonskip" style="cursor: default; padding: 0 4; margin-right: 8px;">
                                    <xsl:value-of select="$fid"/>
                                </span>

                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>

                                <font style="margin-left: 8px; color: #666666;">[<xsl:value-of select="skipped/@message"/>]</font>
                                    </li>
                                </xsl:when>
                            </xsl:choose>
                        </xsl:for-each>
                    </ul>
                </div>
                <!-- TESTS RESULTS SECTION -->
                <div style="margin-top: 20px">
                <h2>All tests results</h2>
                <xsl:for-each select="testcase">
                    <xsl:variable name="id" select="position()"/>
                    <xsl:variable name="fid" select="format-number($id, '000')"/>
                    <xsl:choose>
                        <xsl:when test="failure or error">
                            <xsl:variable name="buttonclass">
                                <xsl:if test="failure">buttonfailed</xsl:if>
                                <xsl:if test="error">buttonerror</xsl:if>
                            </xsl:variable>
                            <li class="failed" id="tst{$id}l">
                                <span id="tst{$id}+" class="{$buttonclass}" onClick="show('tst{$id}')">
                                +
                                    <xsl:value-of select="$fid"/>
                                +</span>
                                <span id="tst{$id}-" class="{$buttonclass}" onClick="hide('tst{$id}')" style="position: absolute; visibility: hidden;">
                                -
                                    <xsl:value-of select="$fid"/>
                                -</span>&#160;
                                <xsl:value-of select="@classname"/>
.
                                <xsl:value-of select="@name"/>
                                <div style="clear: both;"></div>
                                <span id="tst{$id}" style="position: absolute; visibility: hidden;">
                                    <div class="embedding">
                                        <pre class="text-box" id="text-{$id}">
                                            <xsl:value-of select="./*"/>
                                        </pre>
                                        <ul class="attachments">
                                            <xsl:for-each select="hierarchies/*">
                                                <xsl:variable name="idh" select="position()"/>
                                                <li class="collapsable" onclick="toggle(this, 'xml-txt');">
                                                    <i class="fa fa-sharp fa-angle-right icon">&#160;</i>
                                                    <a class="header"><xsl:value-of select="@name"/></a>
                                                    <div class="contents" style="display:none">
                                                        <div class="xml-box">
                                                            <div class="xml-txt" id="hierarchy-{$id}.{$idh}" style="display:none"></div>
                                                        </div>
                                                    </div>
                                                </li>
                                            </xsl:for-each>
                                            <xsl:for-each select="screenshots/*">
                                                <xsl:variable name="ids" select="position()"/>
                                                <li class="collapsable" onclick="toggle(this, 'img');">
                                                    <i class="fa fa-sharp fa-angle-right icon">&#160;</i>
                                                    <a class="header"><xsl:value-of select="@name"/></a>
                                                    <div class="contents" style="display:none">
                                                        <div class="image-box">
                                                            <img class="img" id="screenshot-{$id}.{$ids}" style="display:none"></img>
                                                        </div>
                                                    </div>
                                                </li>
                                            </xsl:for-each>
                                        </ul>
                                    </div>
                                </span>
                                <div style="clear: both;"></div>
                            </li>
                        </xsl:when>
                        <xsl:when test="skipped">
                            <li class="skipped" id="tst{$id}l">
                                <span id="tst{$id}+" class="buttonskip" onClick="show('tst{$id}')">+
                                    <xsl:value-of select="$fid"/>
                                    +</span>
                                <span id="tst{$id}-" class="buttonskip" onClick="hide('tst{$id}')" style="POSITION: absolute; VISIBILITY: hidden;">
                                    -
                                    <xsl:value-of select="$fid"/>
                                    -</span>&#160;
                                <xsl:value-of select="@classname"/>
                                .
                                <xsl:value-of select="@name"/>
                                <span id="tst{$id}" style="position: absolute; visibility: hidden;">
                                    <pre class="skip-text" >
                                        <xsl:value-of select="skipped/@message"/>
                                    </pre>
                                </span>
                            </li>
                        </xsl:when>
                        <xsl:otherwise>
                            <li class="passed" id="tst{$id}l">
                                <div id="tst{$id}" onClick="toggleButtonPassed(this, {$id})" style="display: inline-block">
                                        <span class="testrow">
                                            <span class="buttonpassed" style="margin-right: 0.73em">
                                                <span class="icon_txt">+</span>
                                                <span style="margin: 0 .6em"><xsl:value-of select="$fid"/></span>
                                                <span class="icon_txt">+</span>
                                            </span>
                                            <xsl:value-of select="@classname"/> . <xsl:value-of select="@name"/>
                                        </span>
                                </div>
                                <div style="clear: both;"></div>
                                <div class="embedding" style="margin-bottom: 0px; border: 0px">
                                    <pre class="text-box-passed" id="text-{$id}" style="display: none">
                                        <xsl:value-of select="system-out"/>
                                    </pre>
                                </div>
                                <div style="clear: both;"></div>
                            </li>
                        </xsl:otherwise>
                    </xsl:choose>
                  </xsl:for-each>
                  </div>
              <script charset="utf-8">
                function embed_attachments() {
                    <xsl:for-each select="testcase">
                        <xsl:variable name="id" select="position()"/>
                        <xsl:choose>
                            <xsl:when test="failure or error">
                                <xsl:for-each select="screenshots/*">
                                    <xsl:variable name="ids" select="position()"/>
                                    var img = document.getElementById("screenshot-" +
                                        "<xsl:value-of select="$id"/>" + '.' + "<xsl:value-of select="$ids"/>");
                                    img.setAttribute('src', "data:image/png;base64," + "<xsl:value-of select="@base64"/>");
                                </xsl:for-each>
                                <xsl:for-each select="hierarchies/*">
                                    <xsl:variable name="idh" select="position()"/>
                                    var hierarchy = document.getElementById("hierarchy-" +
                                        "<xsl:value-of select="$id"/>" + '.' + "<xsl:value-of select="$idh"/>");
                                    hierarchy.innerHTML = `<xsl:value-of select="./text()"/>`;
                                    var text_box = document.getElementById("text-" + "<xsl:value-of select="$id"/>");
                                    hierarchy.style.width = text_box.clientWidth - 40;
                                    <xsl:text disable-output-escaping="yes">
                                    hierarchy.addEventListener("click", e => {e.stopPropagation()});
                                    </xsl:text>
                                </xsl:for-each>
                            </xsl:when>
                        </xsl:choose>
                    </xsl:for-each>
                }
            </script>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
