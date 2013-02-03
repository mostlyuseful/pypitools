# Completion for pip install

function __fish_pip_autocomplete_packages --description 'Test if pip should have the package list as completion'
	for i in (commandline -opc)
		if contains -- $i contains install
			return 0
		end
	end
	return 1
end

complete -c pip -n '__fish_pip_autocomplete_packages' -a '(pypiautocompleter.py)'
