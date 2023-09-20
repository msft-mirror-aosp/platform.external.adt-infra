<?xml version="1.0" encoding="UTF-8" ?>
<!-- Xslt template for displaying Skipped tests. -->
<xsl:stylesheet version="1.0"
                xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
    <xsl:template match = "/testsuites">
        <html>
            <head>
                <title> Skipped Tests Report
                </title>
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
                    li.test_row { padding: 2 0;}
                    span.reason { padding-left: 5px; color: #666666;}

                </style>
            </head>
            <body>
                <h1>Skipped Tests</h1>
                <h2>Platforms:</h2>
                <xsl:for-each select="all_testsuites/platforms/platform">
                    <xsl:variable name="ntests" select="count(./test)"/>
                    <xsl:if test="$ntests &gt; 0">
                        <div style="padding-left: 10px">
                            <h3><xsl:value-of select="@fullname"/> (<xsl:value-of select="$ntests"/>)</h3>
                            <ul>
                                <xsl:for-each select="test">
                                    <li class="test_row"> <xsl:value-of select="nodeid"/>
                                        <span class="reason">
                                            (<xsl:value-of select="reason"/>)
                                        </span>
                                    </li>
                                </xsl:for-each>
                            </ul>
                        </div>
                    </xsl:if>
                </xsl:for-each>
                &#160;
                <div>
                    <h1>Skipped Tests (by Test Suite)</h1>
                    <xsl:for-each select="./testsuite">
                        <div style="margin-bottom: 30px">
                            <font style="color: #555555;"><h1><xsl:value-of select="@name"/></h1></font>
                            <h2>Platforms:</h2>
                            <xsl:for-each select="./platforms/platform">
                                <xsl:variable name="ntests" select="count(./test)"/>
                                <xsl:if test="$ntests &gt; 0">
                                    <div style="padding-left: 10px">
                                        <h3><xsl:value-of select="@fullname"/> (<xsl:value-of select="$ntests"/>)</h3>
                                        <ul>
                                            <xsl:for-each select="test">
                                                <li class="test_row"> <xsl:value-of select="nodeid"/>
                                                    <span class="reason">
                                                        (<xsl:value-of select="reason"/>)
                                                    </span>
                                                </li>
                                            </xsl:for-each>
                                        </ul>
                                    </div>
                                </xsl:if>
                            </xsl:for-each>
                        </div>
                    </xsl:for-each>
                </div>
            </body>
        </html>
    </xsl:template>
</xsl:stylesheet>
