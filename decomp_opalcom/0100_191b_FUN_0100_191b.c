
void FUN_0100_191b(void)

{
  undefined2 uVar1;
  int iVar2;
  int iVar3;
  undefined1 *unaff_SI;
  char *pcVar4;
  undefined2 unaff_DS;
  
  uVar1 = *(undefined2 *)0x2c;
  pcVar4 = (char *)0x0;
FUN_0100_1923:
  do {
    iVar3 = -1;
    if ((*pcVar4 == '\0') && (pcVar4[1] == '\0')) {
      *unaff_SI = 0;
      return;
    }
    do {
      iVar2 = iVar3 + 1;
      if (unaff_SI[iVar2] == '\n') goto FUN_0000_2949;
      iVar3 = iVar2;
    } while (pcVar4[iVar2] == unaff_SI[iVar2]);
    pcVar4 = pcVar4 + 1;
  } while( true );
FUN_0000_2949:
  do {
    iVar3 = iVar3 + 1;
  } while (pcVar4[iVar3] == ' ');
  if (pcVar4[iVar3] == '=') {
    do {
      iVar3 = iVar3 + 1;
    } while (pcVar4[iVar3] == ' ');
    FUN_0100_1722(pcVar4 + iVar3);
    return;
  }
  goto FUN_0100_1923;
}

