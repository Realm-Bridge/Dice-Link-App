// Dice Link Companion - Setup Instructions
export default function Home() {
  return (
    <main className="min-h-screen bg-zinc-950 text-zinc-100 p-8">
      <div className="max-w-3xl mx-auto">
        <h1 className="text-4xl font-bold mb-2 text-zinc-50">Dice Link Companion</h1>
        <p className="text-lg text-zinc-400 mb-8">
          A desktop app for Foundry VTT that lets you roll physical dice
        </p>

        {/* Important Notice */}
        <div className="bg-blue-950 border border-blue-800 rounded-lg p-6 mb-6">
          <p className="text-blue-200 font-semibold mb-2">✓ This is now a Desktop App!</p>
          <p className="text-blue-100">
            This app now launches as a native desktop application window, not in your browser. Follow the steps below to get started.
          </p>
        </div>

        {/* Prerequisites */}
        <div className="bg-amber-950 border border-amber-800 rounded-lg p-6 mb-6">
          <p className="font-semibold text-amber-200">Before You Start - Install Python First</p>
          <p className="text-amber-100 mb-4">You need to install Python on your computer.</p>
          <div className="space-y-4">
            <div>
              <p className="font-semibold text-amber-200">Windows:</p>
              <ol className="list-decimal list-inside text-amber-100 space-y-1 ml-2">
                <li>Go to <span className="text-amber-300">python.org/downloads</span></li>
                <li>Click the big yellow "Download Python" button</li>
                <li>Run the installer</li>
                <li>IMPORTANT: Tick the box that says "Add Python to PATH"</li>
                <li>Click "Install Now"</li>
              </ol>
            </div>
            <div>
              <p className="font-semibold text-amber-200">Mac:</p>
              <ol className="list-decimal list-inside text-amber-100 space-y-1 ml-2">
                <li>Go to <span className="text-amber-300">python.org/downloads</span></li>
                <li>Click the big yellow "Download Python" button</li>
                <li>Open the downloaded file and follow the installer</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Step 1 */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-zinc-50">Step 1: Download the App</h2>
          <ol className="list-decimal list-inside text-zinc-300 space-y-3">
            <li>Look at the top-right corner of this v0 page</li>
            <li>Click the three dots menu (...)</li>
            <li>Click "Download ZIP"</li>
            <li>Save the ZIP file somewhere you can find it (like your Desktop)</li>
            <li>Find the ZIP file and double-click it to extract/unzip it</li>
          </ol>
        </div>

        {/* Step 2 */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-zinc-50">Step 2: Open Terminal/Command Prompt</h2>
          <div className="space-y-4">
            <div>
              <p className="font-semibold text-zinc-300">On Windows:</p>
              <ol className="list-decimal list-inside text-zinc-400 space-y-1 ml-2">
                <li>Press the Windows key on your keyboard</li>
                <li>Type "cmd"</li>
                <li>Click on "Command Prompt"</li>
              </ol>
            </div>
            <div>
              <p className="font-semibold text-zinc-300">On Mac:</p>
              <ol className="list-decimal list-inside text-zinc-400 space-y-1 ml-2">
                <li>Press Command + Space</li>
                <li>Type "Terminal"</li>
                <li>Press Enter</li>
              </ol>
            </div>
          </div>
        </div>

        {/* Step 3 */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-zinc-50">Step 3: Go to the App Folder</h2>
          <p className="text-zinc-400 mb-4">In the terminal window, type this command and press Enter:</p>
          <code className="block bg-zinc-800 p-3 rounded text-sm font-mono text-green-400">
            cd "C:\Users\user\Desktop\Dice Link\Dice Link App\Dice Link App\scripts\dice-link"
          </code>
          <p className="text-zinc-500 text-sm mt-2">(Replace the path with where YOU extracted the ZIP file)</p>
        </div>

        {/* Step 4 */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-zinc-50">Step 4: Install Dependencies</h2>
          <p className="text-zinc-400 mb-4">Type this command and press Enter:</p>
          <code className="block bg-zinc-800 p-3 rounded text-sm font-mono text-green-400">
            pip install -r requirements.txt
          </code>
          <p className="text-zinc-500 text-sm mt-2">
            (Wait for it to finish - you will see text scrolling, then it will stop. This only needs to be done once)
          </p>
        </div>

        {/* Step 5 */}
        <div className="bg-green-950 border border-green-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-green-200">Step 5: Start the Desktop App</h2>
          <p className="text-green-100 mb-4">Type this command and press Enter:</p>
          <code className="block bg-green-900 p-3 rounded text-sm font-mono text-green-300">
            python main.py
          </code>
          <p className="text-green-200 font-semibold mt-3">What happens next:</p>
          <ul className="list-disc list-inside text-green-100 space-y-2 mt-2 ml-2">
            <li>You will see some startup text in the Command Prompt</li>
            <li>A new window titled "Dice Link" will appear on your screen</li>
            <li>This is the Dice Link app! You can now use it</li>
            <li>The Command Prompt window will keep running in the background</li>
          </ul>
        </div>

        {/* Testing */}
        <div className="bg-purple-950 border border-purple-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-purple-200">Step 6: Test the App</h2>
          <p className="text-purple-100 mb-4">The Dice Link window should show:</p>
          <ul className="list-disc list-inside text-purple-100 space-y-2 ml-2 mb-4">
            <li>"Dice Link" at the top</li>
            <li>A red "Disconnected" status (this is normal if Foundry VTT isn't connected)</li>
            <li>"Waiting for Foundry VTT" message</li>
            <li>A "Send Test Roll" button</li>
          </ul>
          <p className="text-purple-100 mb-3">To test without Foundry VTT:</p>
          <ol className="list-decimal list-inside text-purple-100 space-y-2 ml-2">
            <li>Click the "Send Test Roll" button in the app</li>
            <li>The app should show a dice roll dialog with test dice (1d20 and 2d6)</li>
            <li>Enter numbers for each die roll</li>
            <li>Click "Submit Results"</li>
            <li>You should see the results get submitted</li>
          </ol>
        </div>

        {/* Connecting to Foundry */}
        <div className="bg-indigo-950 border border-indigo-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-indigo-200">Connecting to Foundry VTT</h2>
          <p className="text-indigo-100 mb-3">Once you have Foundry VTT installed and the Dice Link Companion module:</p>
          <ol className="list-decimal list-inside text-indigo-100 space-y-2 ml-2 mb-4">
            <li>In Foundry VTT module settings, find the Dice Link Companion module</li>
            <li>Set the connection address to:</li>
          </ol>
          <code className="block bg-indigo-900 p-3 rounded text-sm font-mono text-indigo-300 mt-2">
            ws://localhost:8765/ws/dlc
          </code>
          <p className="text-indigo-100 mt-3">
            When you connect, the red "Disconnected" status will turn green and say "Connected"
          </p>
        </div>

        {/* Running Again */}
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg p-6 mb-4">
          <h2 className="text-xl font-semibold mb-4 text-zinc-50">Running the App Again (Next Time)</h2>
          <p className="text-zinc-400 mb-4">You only need to do Steps 3, 4, and 5 the first time. After that:</p>
          <ol className="list-decimal list-inside text-zinc-300 space-y-2 ml-2">
            <li>Open Command Prompt</li>
            <li>Type: <code className="bg-zinc-800 px-2 py-1 rounded text-green-400">cd "C:\Users\user\Desktop\Dice Link\Dice Link App\Dice Link App\scripts\dice-link"</code></li>
            <li>Type: <code className="bg-zinc-800 px-2 py-1 rounded text-green-400">python main.py</code></li>
            <li>The Dice Link window opens - you're ready to use it!</li>
          </ol>
        </div>

        {/* Stopping */}
        <div className="bg-red-950 border border-red-800 rounded-lg p-6">
          <h2 className="text-xl font-semibold mb-4 text-red-200">How to Stop the App</h2>
          <ol className="list-decimal list-inside text-red-100 space-y-2 ml-2">
            <li>Close the Dice Link window by clicking the X button in the top-right corner</li>
            <li>Go back to the Command Prompt window</li>
            <li>Press <kbd className="bg-red-900 px-2 py-1 rounded text-red-200">Ctrl</kbd> + <kbd className="bg-red-900 px-2 py-1 rounded text-red-200">C</kbd></li>
            <li>The app will stop running</li>
          </ol>
        </div>
      </div>
    </main>
  )
}
