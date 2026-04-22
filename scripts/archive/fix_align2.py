# wait I need the original file! 
# is there any backup?
import glob
print(glob.glob("*.bak*") + glob.glob("**/*.bak", recursive=True))
