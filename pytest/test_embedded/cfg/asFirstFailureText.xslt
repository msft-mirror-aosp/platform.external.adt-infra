<?xml version="1.0" encoding="UTF-8" ?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
<xsl:output method="xml" omit-xml-declaration="yes" />
<xsl:template match="testsuite">
<xsl:apply-templates select="(//failure)[1]"/>
<xsl:apply-templates select="(//error)[1]"/>
</xsl:template>
<xsl:template match="//failure">
-- TEST FAILED:  <xsl:value-of select="../@classname"/><xsl:value-of select="../@name"/> --
<xsl:text>&#10;</xsl:text>
<xsl:value-of select="."  disable-output-escaping="yes" />
</xsl:template>
 <xsl:template match="//error">
-- TEST ERROR: <xsl:value-of select="../@classname"/><xsl:value-of select="../@name"/> --
<xsl:text>&#10;</xsl:text>
<xsl:value-of select="."  disable-output-escaping="yes" />
</xsl:template>
</xsl:stylesheet>
