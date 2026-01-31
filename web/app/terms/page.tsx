import Link from "next/link";

export default function TermsOfService() {
  return (
    <div className="min-h-screen bg-terminal-bg text-terminal-text">
      <div className="max-w-4xl mx-auto px-6 py-12">
        <h1 className="text-3xl font-bold text-terminal-accent mb-2">Terms of Service</h1>
        <p className="text-terminal-muted mb-8">Last updated: January 31, 2026</p>

        <div className="space-y-8 text-terminal-text/90">
          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">1. Agreement to Terms</h2>
            <p className="mb-3">
              By accessing or using JohnnyBets (&quot;the Service&quot;), you agree to be bound by these Terms of Service. 
              If you do not agree to these terms, do not use the Service.
            </p>
            <p>
              JohnnyBets is operated by JohnnyBets (&quot;we,&quot; &quot;us,&quot; or &quot;our&quot;). We reserve the right to 
              modify these terms at any time. Continued use of the Service after changes constitutes acceptance of the new terms.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">2. Description of Service</h2>
            <p className="mb-3">
              JohnnyBets is a sports betting analytics platform that provides:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 mb-3">
              <li>Real-time odds aggregation from multiple sportsbooks</li>
              <li>Statistical analysis and matchup context</li>
              <li>AI-powered betting insights and research tools</li>
              <li>Arbitrage and value opportunity identification</li>
            </ul>
            <p className="font-semibold">
              The Service provides information and analysis only. We do not accept bets, process wagers, 
              or operate as a sportsbook in any jurisdiction.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">3. Important Disclaimers</h2>
            
            <h3 className="font-semibold mt-4 mb-2">Not Financial or Gambling Advice</h3>
            <p className="mb-3">
              All information provided by JohnnyBets is for informational and entertainment purposes only. 
              Nothing on this platform constitutes financial advice, gambling advice, or a recommendation to place any bet. 
              You are solely responsible for your own betting decisions and any resulting gains or losses.
            </p>

            <h3 className="font-semibold mt-4 mb-2">No Guarantees</h3>
            <p className="mb-3">
              We do not guarantee the accuracy, completeness, or timeliness of any information provided. 
              Sports betting involves risk, and past performance does not guarantee future results. 
              Odds, lines, and statistics can change rapidly and may not reflect current market conditions.
            </p>

            <h3 className="font-semibold mt-4 mb-2">Responsible Gambling</h3>
            <p>
              Gambling can be addictive. If you or someone you know has a gambling problem, please contact the 
              National Council on Problem Gambling at 1-800-522-4700 or visit{" "}
              <a href="https://www.ncpgambling.org" className="text-terminal-accent hover:underline" target="_blank" rel="noopener noreferrer">
                ncpgambling.org
              </a>. 
              Only gamble with money you can afford to lose. Set limits and stick to them.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">4. Eligibility</h2>
            <p className="mb-3">
              You must be at least 18 years old (or the legal gambling age in your jurisdiction, whichever is higher) 
              to use this Service. By using JohnnyBets, you represent and warrant that you meet these age requirements.
            </p>
            <p>
              You are responsible for ensuring that your use of sports betting information complies with all 
              applicable laws in your jurisdiction. Sports betting is not legal in all locations.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">5. User Accounts</h2>
            <p className="mb-3">
              To access certain features, you may need to create an account. You agree to:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Provide accurate and complete registration information</li>
              <li>Maintain the security of your account credentials</li>
              <li>Notify us immediately of any unauthorized access</li>
              <li>Accept responsibility for all activity under your account</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">6. Prohibited Conduct</h2>
            <p className="mb-3">You agree not to:</p>
            <ul className="list-disc list-inside space-y-1 ml-4">
              <li>Use the Service for any illegal purpose</li>
              <li>Attempt to gain unauthorized access to our systems</li>
              <li>Interfere with or disrupt the Service</li>
              <li>Scrape, copy, or redistribute our content without permission</li>
              <li>Use automated systems to access the Service in a manner that exceeds reasonable use</li>
              <li>Impersonate any person or entity</li>
              <li>Use the Service to harass, abuse, or harm others</li>
            </ul>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">7. Intellectual Property</h2>
            <p>
              All content, features, and functionality of the Service—including but not limited to text, graphics, 
              logos, icons, images, audio clips, data compilations, and software—are the exclusive property of 
              JohnnyBets or its licensors and are protected by copyright, trademark, and other intellectual property laws.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">8. Third-Party Services</h2>
            <p className="mb-3">
              The Service may integrate with or display information from third-party services, including but not limited to:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 mb-3">
              <li>Sportsbook odds providers</li>
              <li>Sports data APIs</li>
              <li>AI/LLM providers</li>
              <li>Authentication providers</li>
            </ul>
            <p>
              We are not responsible for the accuracy, availability, or content of third-party services. 
              Your use of third-party services is subject to their respective terms and privacy policies.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">9. Limitation of Liability</h2>
            <p className="mb-3">
              TO THE MAXIMUM EXTENT PERMITTED BY LAW, JOHNNYBETS AND ITS OFFICERS, DIRECTORS, EMPLOYEES, 
              AND AGENTS SHALL NOT BE LIABLE FOR ANY INDIRECT, INCIDENTAL, SPECIAL, CONSEQUENTIAL, OR 
              PUNITIVE DAMAGES, INCLUDING BUT NOT LIMITED TO:
            </p>
            <ul className="list-disc list-inside space-y-1 ml-4 mb-3">
              <li>Loss of profits, revenue, or data</li>
              <li>Gambling losses of any kind</li>
              <li>Losses arising from reliance on information provided by the Service</li>
              <li>Losses arising from service interruptions or errors</li>
            </ul>
            <p>
              OUR TOTAL LIABILITY FOR ANY CLAIM ARISING FROM YOUR USE OF THE SERVICE SHALL NOT EXCEED 
              THE AMOUNT YOU PAID TO US, IF ANY, IN THE TWELVE (12) MONTHS PRECEDING THE CLAIM.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">10. Indemnification</h2>
            <p>
              You agree to indemnify, defend, and hold harmless JohnnyBets and its officers, directors, 
              employees, and agents from any claims, damages, losses, liabilities, and expenses (including 
              reasonable attorneys&apos; fees) arising from your use of the Service, violation of these terms, 
              or infringement of any third-party rights.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">11. Termination</h2>
            <p>
              We may terminate or suspend your access to the Service at any time, with or without cause, 
              with or without notice. Upon termination, your right to use the Service will immediately cease. 
              All provisions of these terms that by their nature should survive termination shall survive.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">12. Governing Law</h2>
            <p>
              These terms shall be governed by and construed in accordance with the laws of the State of Delaware, 
              United States, without regard to its conflict of law provisions. Any disputes arising from these 
              terms or your use of the Service shall be resolved in the state or federal courts located in Delaware.
            </p>
          </section>

          <section>
            <h2 className="text-xl font-semibold text-terminal-accent mb-3">13. Contact</h2>
            <p>
              For questions about these Terms of Service, please contact us at{" "}
              <a href="mailto:mail@johnnybets.ai" className="text-terminal-accent hover:underline">
                mail@johnnybets.ai
              </a>.
            </p>
          </section>
        </div>

        <div className="mt-12 pt-8 border-t border-terminal-border">
          <Link href="/" className="text-terminal-accent hover:underline">&larr; Back to JohnnyBets</Link>
        </div>
      </div>
    </div>
  );
}
