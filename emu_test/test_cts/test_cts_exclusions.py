"""CTS test exclusions specification"""

#
# format:
#  Let
#    <test-spec> ::= <fully-qualified-class-name>#<test-method-name> in
#    <test-spec-seq> ::= '[' <test-spec> {, <test-spec> }* ']'
#    <package-spec> ::= <package> : <test-spec-seq>
#  in
#    '{' <plan> ':' '{' <package-spec> {, <package-spec> }* '}'

# Bugs for current exclusions:
#   android.trustedvoice.cts.TrustedVoiceHostTest#testLogcat: b/29270651

def cts_plans_current_exclusions():
    return { 'CTS' : { 'android.host.trustedvoice' :
                       [ 'android.trustedvoice.cts.TrustedVoiceHostTest#testLogcat' ]
                     } }
